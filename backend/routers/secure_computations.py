from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union
import csv
import io
from models import SecureComputation, ComputationParticipant, ComputationResult, Organization, ComputationInvitation, ComputationPatientRecord
from dependencies import get_db, get_current_user, require_permissions
from auth_utils import Permission
from secure_computation import SecureComputationService, SecureHealthMetricsComputation
from advanced_smpc_computations import AdvancedSMPCComputations
from homomorphic_encryption_enhanced import EnhancedHomomorphicEncryption
from smpc_protocols import ShamirSecretSharing
from secure_computation_export import SecureComputationExport
from pydantic import BaseModel, Field
from datetime import datetime
import logging
import json

# Set up logging for this module
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

# -------------------------- Available Computations -------------------------- #
@router.get("/available-computations")
def get_available_computations(
    current_user: dict = Depends(get_current_user)
):
    """Return all available computation types with their descriptions and requirements"""
    try:
        # Initialize advanced SMPC to get available computations
        advanced_smpc = AdvancedSMPCComputations()
        advanced_computations = advanced_smpc.get_available_computations()

        # Basic computations
        basic_computations = {
            "average": {
                "name": "Average",
                "description": "Calculate the arithmetic mean of numeric values",
                "category": "basic_statistics",
                "min_participants": 1,
                "data_requirements": ["numeric_values"],
                "security_methods": ["standard", "homomorphic"],
                "example_use_case": "Calculate average patient age across hospitals"
            },
            "sum": {
                "name": "Sum",
                "description": "Calculate the total sum of numeric values",
                "category": "basic_statistics",
                "min_participants": 1,
                "data_requirements": ["numeric_values"],
                "security_methods": ["standard", "homomorphic"],
                "example_use_case": "Calculate total number of patients across regions"
            },
            "count": {
                "name": "Count",
                "description": "Count the number of records or data points",
                "category": "basic_statistics",
                "min_participants": 1,
                "data_requirements": ["any_data"],
                "security_methods": ["standard"],
                "example_use_case": "Count total medical procedures performed"
            },
            "secure_average": {
                "name": "Secure Average",
                "description": "Privacy-preserving average using SMPC",
                "category": "secure_statistics",
                "min_participants": 2,
                "data_requirements": ["numeric_values"],
                "security_methods": ["hybrid"],
                "example_use_case": "Calculate average treatment costs without revealing individual hospital data"
            },
            "secure_sum": {
                "name": "Secure Sum",
                "description": "Privacy-preserving sum using SMPC",
                "category": "secure_statistics",
                "min_participants": 2,
                "data_requirements": ["numeric_values"],
                "security_methods": ["hybrid"],
                "example_use_case": "Calculate total adverse events without revealing source organizations"
            },
            "secure_variance": {
                "name": "Secure Variance",
                "description": "Privacy-preserving variance calculation using SMPC",
                "category": "secure_statistics",
                "min_participants": 2,
                "data_requirements": ["numeric_values"],
                "security_methods": ["hybrid"],
                "example_use_case": "Measure variability in treatment outcomes across institutions"
            }
        }

        # Combine basic and advanced computations
        all_computations = {**basic_computations, **advanced_computations}

        # Group by category for better organization
        categorized = {}
        for comp_id, comp_info in all_computations.items():
            category = comp_info.get("category", "other")
            if category not in categorized:
                categorized[category] = {}
            categorized[category][comp_id] = comp_info

        return {
            "computations": all_computations,
            "categories": categorized,
            "total_count": len(all_computations),
            "categories_count": len(categorized)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get available computations: {str(e)}")

# -------------------------- Organizations List -------------------------- #
@router.get("/organizations")
def list_organizations(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Return a list of organizations available for invitations.
    Excludes the current caller's organization. The `online` flag is provided
    as a best-effort indicator (set to False by default; can be enhanced with
    websocket presence if desired).
    """
    try:
        caller_id = current_user.get("id") or current_user.get("org_id") or current_user.get("user_id")
        orgs = db.query(Organization).all()
        results: List[Dict[str, Any]] = []
        for org in orgs:
            # Exclude the caller org if known
            if caller_id is not None and str(org.id) == str(caller_id):
                continue
            results.append({
                "id": org.id,
                "name": org.name or org.email or f"Organization {org.id}",
                "email": org.email,
                "online": False  # TODO: integrate with websocket presence if available
            })
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list organizations: {str(e)}")

class ComputationCreate(BaseModel):
    computation_type: str
    participating_orgs: List[str] = Field(default=[], description="Legacy field - use invited_org_ids instead")
    invited_org_ids: Optional[List[int]] = Field(default=None, description="List of organization IDs to invite")
    security_method: Optional[str] = Field(default="standard", description="Security method to use: 'standard', 'homomorphic', or 'hybrid'")
    threshold: Optional[int] = Field(default=2, description="Threshold for SMPC (only used with 'hybrid' security method)")
    min_participants: Optional[int] = Field(default=3, description="Minimum number of participants required for computation")

class ComputationResponse(BaseModel):
    computation_id: str
    type: str
    status: str
    result: Dict[str, Any] = None
    created_at: str
    completed_at: str = None
    security_method: str = None
    encryption_type: str = None
    participants_count: int = None
    submissions_count: int = None
    verified: bool = None
    verification_details: Dict[str, Any] = None

class MetricSubmission(BaseModel):
    value: Union[float, List[float], Dict[str, Any]]
    encryption_type: Optional[str] = Field(default=None, description="Type of encryption: 'standard', 'homomorphic', or 'smpc'")
    shares_info: Optional[Dict[str, Any]] = Field(default=None, description="Additional information for SMPC shares")

class ExportRequest(BaseModel):
    format: str = Field(default="json", description="Export format: 'json' or 'csv'")
    include_sensitive_data: bool = Field(default=False, description="Whether to include sensitive data in the export")

@router.post("/create")
async def create_computation(
    computation: ComputationCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    try:
        print(f"=== CREATE COMPUTATION DEBUG ===")
        print(f"Current user payload: {current_user}")
        print(f"Computation data: {computation}")

        service = SecureComputationService(db)

        # Get user ID - handle different possible structures
        user_id_str = None
        if "id" in current_user:
            user_id_str = current_user["id"]
        elif "user_id" in current_user:
            user_id_str = current_user["user_id"]
        elif "sub" in current_user:
            user_id_str = current_user["sub"]
        else:
            print(f"ERROR: Could not find user ID in current_user: {current_user}")
            raise HTTPException(
                status_code=400,
                detail="Invalid user authentication data"
            )

        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            print(f"ERROR: Invalid user ID format: {user_id_str}")
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        print(f"Using user_id: {user_id}")

        # Map security method to computation type if needed
        computation_type = computation.computation_type
        if computation.security_method == "hybrid" and not computation_type.startswith("secure_"):
            computation_type = f"secure_{computation_type}"

        print(f"Final computation_type: {computation_type}")

        # Prepare computation parameters (used by secure_average and advanced secure types)
        parameters: Dict[str, Any] = {}
        if computation.threshold is not None:
            parameters["threshold"] = computation.threshold

        # For now, treat secure_average as a blood sugar metric by default
        if computation_type == "secure_average":
            parameters.setdefault("metric", "blood_sugar")

        # Use new invitation-based system if specific organizations are invited
        if computation.invited_org_ids:
            print(f"Creating computation with invitations: {computation.invited_org_ids}")
            computation_id = service.create_computation_with_invitations(
                user_id,
                computation_type,
                computation.invited_org_ids,
                computation.security_method,
                parameters=parameters
            )
        else:
            # Legacy: create public computation (not recommended)
            print("Creating public computation")
            computation_id = service.create_computation(
                user_id,
                computation_type,
                make_public=True,
                security_method=computation.security_method,
                parameters=parameters
            )

        print(f"Created computation with ID: {computation_id}")

        # Initialize secure computation with security parameters
        try:
            metrics_computation = SecureHealthMetricsComputation()
            metrics_computation.initialize_computation(
                computation_id,
                computation_type,
                computation.participating_orgs,
                security_method=computation.security_method,
                threshold=computation.threshold,
                min_participants=computation.min_participants
            )
            print("Initialized SecureHealthMetricsComputation")
        except Exception as metrics_error:
            print(f"Warning: Failed to initialize SecureHealthMetricsComputation: {metrics_error}")
            # Continue without failing the entire request

        # Get the computation result with security method information
        result = service.get_computation_result(computation_id, user_id)

        # Add security method information
        if result:
            result["security_method"] = computation.security_method
            result["computation_id"] = computation_id
        else:
            # Fallback result if get_computation_result fails
            result = {
                "computation_id": computation_id,
                "type": computation_type,
                "status": "initialized",
                "security_method": computation.security_method,
                "created_at": datetime.utcnow().isoformat()
            }

        print(f"Returning result: {result}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR in create_computation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create computation: {str(e)}"
        )



@router.get("/pending-requests", response_model=List[Dict[str, Any]])
async def get_pending_requests(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        service = SecureComputationService(db)

        # Get user ID - handle different possible structures
        user_id_str = current_user.get("id") or current_user.get("user_id") or current_user.get("sub") or current_user.get("org_id")
        if not user_id_str:
            raise HTTPException(status_code=400, detail="Invalid user authentication data")

        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        pending_requests = await service.get_pending_requests(user_id)
        return pending_requests
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get pending requests: {str(e)}"
        )

@router.post("/computations/{computation_id}/accept")
async def accept_computation_request(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    try:
        service = SecureComputationService(db)

        # Get user ID - handle different possible structures
        user_id_str = current_user.get("id") or current_user.get("user_id") or current_user.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=400, detail="Invalid user authentication data")

        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        success = await service.accept_computation_request(computation_id, user_id, user_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Computation not found or you're not authorized to accept this request"
            )
        return {"status": "success", "message": "Computation request accepted"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to accept computation request: {str(e)}"
        )

@router.post("/computations/{computation_id}/decline")
async def decline_computation_request(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    try:
        service = SecureComputationService(db)

        # Get user ID - handle different possible structures
        user_id_str = current_user.get("id") or current_user.get("user_id") or current_user.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=400, detail="Invalid user authentication data")

        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        success = await service.decline_computation_request(computation_id, user_id, user_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Computation not found or you're not authorized to decline this request"
            )
        return {"status": "success", "message": "Computation request declined"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to decline computation request: {str(e)}"
        )

@router.post("/computations/{computation_id}/join")
async def join_computation(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        service = SecureComputationService(db)

        # Get user ID - handle different possible structures
        user_id_str = current_user.get("id") or current_user.get("user_id") or current_user.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=400, detail="Invalid user authentication data")

        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        success = await service.join_computation(computation_id, user_id)
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Computation not found"
            )
        return {"message": "Successfully joined computation"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to join computation: {str(e)}"
        )

@router.post("/computations/{computation_id}/submit-csv")
async def submit_csv_data(
    computation_id: str,
    file: UploadFile = File(...),
    description: str = Form(""),
    security_method: str = Form("standard"),
    has_header: bool = Form(True),
    delimiter: str = Form(","),
    column: Optional[str] = Form(None),
    columns: Optional[str] = Form(None),
    column_index: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Submit data via CSV file upload"""
    try:
        print(f"=== CSV Submission Debug ===")
        print(f"Computation ID: {computation_id}")
        print(f"User ID: {current_user.get('id')}")
        print(f"File: {file.filename}")
        
        service = SecureComputationService(db)
        
        # Get the computation first
        computation = db.query(SecureComputation).filter_by(computation_id=computation_id).first()
        if not computation:
            print(f"Computation {computation_id} not found")
            raise HTTPException(
                status_code=404,
                detail="Computation not found"
            )
            
        print(f"Found computation: {computation.computation_id}, creator: {computation.org_id}")
        
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail="Only CSV files are allowed"
            )
        
        # Read and parse CSV file
        content = await file.read()
        csv_data = content.decode('utf-8')
        
        # Parse CSV with optional header and column selection
        data_points: Union[List[float], Dict[str, List[float]]] = []
        selected_columns: List[str] = []
        patient_rows_for_records: List[Dict[str, Any]] = []
        patient_metric_column: Optional[str] = None
        patient_id_column: Optional[str] = None

        # Helper to try parse float safely
        def to_float(x: Any) -> Optional[float]:
            try:
                return float(str(x).strip())
            except Exception:
                return None

        if has_header:
            reader = csv.DictReader(io.StringIO(csv_data), delimiter=delimiter or ",")
            headers = reader.fieldnames or []
            print(f"CSV headers detected: {headers}")

            # Identify potential patient ID column for secure_average computations
            if computation.type and computation.type.lower() == "secure_average":
                for h in headers:
                    if not h:
                        continue
                    h_norm = h.strip().lower()
                    if h_norm in ["patientid", "patient_id", "patient id"]:
                        patient_id_column = h
                        break

            rows = list(reader)

            # Determine which columns to extract
            if columns:
                selected_columns = [c.strip() for c in columns.split(',') if c.strip()]
            elif column:
                selected_columns = [column.strip()]
            else:
                # Default to first header if available
                selected_columns = headers[:1]

            # Validate columns exist
            missing = [c for c in selected_columns if c not in headers]
            if missing:
                raise HTTPException(status_code=400, detail=f"Missing columns in CSV header: {missing}")

            if len(selected_columns) == 1:
                col = selected_columns[0]
                values: List[float] = []
                for row in rows:
                    val = to_float(row.get(col))
                    if val is not None:
                        values.append(val)

                        # Capture per-patient metric rows for secure_average
                        if computation.type and computation.type.lower() == "secure_average" and patient_id_column:
                            pid = row.get(patient_id_column)
                            if pid is not None and str(pid).strip() != "":
                                patient_rows_for_records.append(
                                    {
                                        "patient_id": str(pid),
                                        "value": float(val),
                                        "metric_name": col,
                                    }
                                )
                data_points = values
            else:
                dp_dict: Dict[str, List[float]] = {c: [] for c in selected_columns}
                for row in rows:
                    for c in selected_columns:
                        val = to_float(row.get(c))
                        if val is not None:
                            dp_dict[c].append(val)
                data_points = dp_dict
        else:
            # No header: use csv.reader
            reader = csv.reader(io.StringIO(csv_data), delimiter=delimiter or ",")
            if columns:
                # Treat as indices list, e.g., "0,2"
                try:
                    idxs = [int(s.strip()) for s in columns.split(',') if s.strip()]
                except Exception:
                    raise HTTPException(status_code=400, detail="Invalid 'columns' indices. Provide comma-separated integers.")
            elif column_index is not None:
                idxs = [int(column_index)]
            else:
                idxs = [0]

            if len(idxs) == 1:
                idx = idxs[0]
                values: List[float] = []
                for row in reader:
                    if not row:
                        continue
                    if idx < 0 or idx >= len(row):
                        continue
                    val = to_float(row[idx])
                    if val is not None:
                        values.append(val)
                data_points = values
            else:
                dp_dict: Dict[str, List[float]] = {str(i): [] for i in idxs}
                for row in reader:
                    if not row:
                        continue
                    for i in idxs:
                        if i < 0 or i >= len(row):
                            continue
                        val = to_float(row[i])
                        if val is not None:
                            dp_dict[str(i)].append(val)
                data_points = dp_dict

        # Validate extracted data
        if isinstance(data_points, list):
            if len(data_points) == 0:
                raise HTTPException(status_code=400, detail="No valid numeric values found in CSV file")
            print(f"Extracted {len(data_points)} data points from CSV (list mode): {data_points[:5]}...")
        else:
            total_vals = sum(len(v) for v in data_points.values())
            if total_vals == 0:
                raise HTTPException(status_code=400, detail="No valid numeric values found in selected CSV columns")
            print(f"Extracted multi-column data from CSV (dict mode): keys={list(data_points.keys())}, total_values={total_vals}")
        
        # Get organization ID from current user (organizations are the users in this system)
        user_org_id_str = current_user["id"]
        if not user_org_id_str:
            raise HTTPException(status_code=400, detail="Invalid user authentication data")

        try:
            user_org_id = int(user_org_id_str)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        print(f"CSV Upload - Using org_id: {user_org_id}")
        
        # Check if user is a participant in this computation
        participant = db.query(ComputationParticipant).filter_by(
            computation_id=computation_id, org_id=user_org_id
        ).first()
        
        print(f"Participant check: {participant}")
        
        if not participant:
            # Auto-join the computation if user is the creator
            if computation.org_id == user_org_id:
                # Creator automatically becomes a participant
                new_participant = ComputationParticipant(
                    computation_id=computation_id,
                    org_id=user_org_id
                )
                db.add(new_participant)
                db.commit()
                print(f"Auto-joined creator {user_org_id} to computation {computation_id}")
            else:
                print(f"User {user_org_id} is not a participant and not the creator")
                raise HTTPException(
                    status_code=403,
                    detail="You must join this computation before submitting data"
                )
        
        # Submit data using the service
        print(f"Calling service.submit_data for CSV with: computation_id={computation_id}, org_id={user_org_id}, data_points={len(data_points)} items")
        result = await service.submit_data(
            computation_id,
            user_org_id,
            data_points
        )
        
        print(f"CSV Service result: {result}")
        
        if not result.get("success", False):
            error_detail = result.get("error", "Failed to submit data")
            error_code = result.get("error_code", "UNKNOWN_ERROR")
            print(f"CSV submission failed: {error_detail} (Code: {error_code})")
            raise HTTPException(
                status_code=400,
                detail=f"{error_detail} (Error Code: {error_code})"
            )
        # Persist per-patient metric records for secure_average computations if available
        try:
            if patient_rows_for_records:
                records: List[ComputationPatientRecord] = []
                for row in patient_rows_for_records:
                    try:
                        records.append(
                            ComputationPatientRecord(
                                computation_id=computation_id,
                                org_id=user_org_id,
                                patient_id=row.get("patient_id"),
                                metric_name=row.get("metric_name"),
                                value=row.get("value"),
                            )
                        )
                    except Exception as rec_err:
                        print(f"Error building ComputationPatientRecord: {rec_err}")
                if records:
                    db.add_all(records)
                    db.commit()
                    print(f"Stored {len(records)} patient records for computation {computation_id}")
        except Exception as store_exc:
            # Do not fail the request if storing detailed records fails
            print(f"Warning: Failed to store patient-level records: {store_exc}")
        
        return {
            "message": "CSV data submitted successfully",
            "data_points_count": len(data_points),
            "filename": file.filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in CSV submission: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process CSV file: {str(e)}"
        )

@router.post("/computations/{computation_id}/submit")
async def submit_data(
    computation_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    print(f"=== ENDPOINT HIT: Data Submission Debug ===")
    print(f"Raw computation_id: {computation_id}")
    print(f"Current user: {current_user}")
    logger.debug(f"Endpoint hit with computation_id: {computation_id}")
    logger.debug(f"User: {current_user}")
    
    # Parse request body manually to avoid Pydantic validation issues
    try:
        body = await request.body()
        print(f"Raw request body: {body}")
        
        import json
        submission_data = json.loads(body.decode('utf-8'))
        print(f"Parsed submission data: {submission_data}")
        
        # Create MetricSubmission object manually
        submission = MetricSubmission(
            value=submission_data.get('value'),
            encryption_type=submission_data.get('encryption_type'),
            shares_info=submission_data.get('shares_info')
        )
        print(f"Created submission object: {submission}")
        
    except Exception as parse_error:
        print(f"Error parsing request: {parse_error}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request format: {str(parse_error)}"
        )
    
    try:
        print(f"=== Inside try block ===")
        print(f"Computation ID: {computation_id}")
        print(f"User ID: {current_user.get('id')}")
        print(f"Submission data: {submission}")
        print(f"Submission value: {submission.value}")
        print(f"Submission value type: {type(submission.value)}")
        
        service = SecureComputationService(db)
        
        # Get the computation to determine security method
        computation = db.query(SecureComputation).filter_by(computation_id=computation_id).first()
        if not computation:
            print(f"Computation {computation_id} not found")
            raise HTTPException(
                status_code=404,
                detail="Computation not found"
            )
            
        print(f"Found computation: {computation.computation_id}, creator: {computation.org_id}")
            
        # Determine encryption type based on computation type and submission
        encryption_type = submission.encryption_type
        if not encryption_type:
            # Auto-detect based on computation type
            if computation.type.startswith("secure_"):
                encryption_type = "hybrid"
            elif computation.type in ["sum", "average", "basic_statistics", "health_statistics"]:
                encryption_type = "homomorphic"
            else:
                encryption_type = "standard"
        
        print(f"Using encryption type: {encryption_type}")

        # Validate encryption type against computation type
        if encryption_type == "hybrid" and not computation.type.startswith("secure_"):
            raise HTTPException(
                status_code=400,
                detail="'hybrid' encryption can only be used with secure computation types (e.g., 'secure_average')"
            )
        
        # Process data based on encryption type
        if isinstance(submission.value, dict):
            # Already formatted data (likely pre-encrypted)
            data = submission.value
        else:
            # Convert single value to list if needed
            data = submission.value if isinstance(submission.value, list) else [submission.value]
        
        print(f"Processed data: {data}")
        
        # Get organization ID from current user (organizations are the users in this system)
        user_org_id_str = current_user["id"]
        if not user_org_id_str:
            raise HTTPException(status_code=400, detail="Invalid user authentication data")

        try:
            user_org_id = int(user_org_id_str)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        print(f"JSON Submit - Using org_id: {user_org_id}")
        
        # Check if user is a participant in this computation
        participant = db.query(ComputationParticipant).filter_by(
            computation_id=computation_id, org_id=user_org_id
        ).first()
        
        print(f"Participant check: {participant}")
        
        if not participant:
            # Auto-join the computation if user is the creator
            if computation.org_id == user_org_id:
                # Creator automatically becomes a participant
                new_participant = ComputationParticipant(
                    computation_id=computation_id,
                    org_id=user_org_id
                )
                db.add(new_participant)
                db.commit()
                print(f"Auto-joined creator {user_org_id} to computation {computation_id}")
            else:
                print(f"User {user_org_id} is not a participant and not the creator")
                raise HTTPException(
                    status_code=403,
                    detail="You must join this computation before submitting data"
                )
        
        # Submit data with encryption type information
        print(f"Calling service.submit_data with: computation_id={computation_id}, org_id={user_org_id}, data={data}")
        result = await service.submit_data(
            computation_id, 
            user_org_id, 
            data
        )
        
        print(f"Service result: {result}")
        
        if not result.get("success", False):
            error_detail = result.get("error", "Failed to submit data")
            error_code = result.get("error_code", "UNKNOWN_ERROR")
            print(f"Data submission failed: {error_detail} (Code: {error_code})")
            
            # Provide detailed error response for debugging
            error_response = {
                "error": error_detail,
                "error_code": error_code,
                "computation_id": computation_id,
                "user_id": user_org_id,
                "debug_info": {
                    "data_type": type(data).__name__,
                    "data_length": len(data) if isinstance(data, (list, dict)) else 1,
                    "encryption_type": encryption_type
                }
            }
            
            raise HTTPException(
                status_code=400,
                detail=error_response
            )
            
        # Add verification data for self-verification feature
        verification_data = {
            "submitted_at": datetime.utcnow().isoformat(),
            "data_points_count": result.get("data_points_count", 0),
            "encryption_type": result.get("encryption_type", encryption_type),
            "data_preview": data[:3] if isinstance(data, list) and len(data) > 0 else "N/A",  # First 3 values for verification
            "computation_id": computation_id,
            "org_id": user_org_id
        }
        
        return {
            "message": "Successfully submitted data",
            "data_points_count": result.get("data_points_count", 0),
            "encryption_type": result.get("encryption_type", encryption_type),
            "verification": verification_data
        }
    except HTTPException as he:
        print(f"=== HTTPException caught ===")
        print(f"Status code: {he.status_code}")
        print(f"Detail: {he.detail}")
        raise
    except Exception as e:
        print(f"=== Unexpected error in submit_data ===")
        print(f"Error type: {type(e)}")
        print(f"Error message: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit data: {str(e)}"
        )

@router.get("/computations/{computation_id}/result", response_model=Dict[str, Any])
def get_computation_result(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # This endpoint remains unchanged as the service.get_computation_result method
    # has been updated to include security method and encryption type information
    try:
        service = SecureComputationService(db)
        # Get the computation first to check its status
        computation = db.query(SecureComputation).filter_by(computation_id=computation_id).first()
        
        if not computation:
            raise HTTPException(
                status_code=404,
                detail="Computation not found"
            )
            
        # Check for error status
        if computation.status == "error":
            return {
                "status": "error",
                "error_message": computation.error_message or "Unknown error occurred",
                "computation_id": computation_id
            }
            
        # Check if computation is still in progress
        if computation.status in ["initialized", "processing", "waiting_for_data", "waiting_for_participants"]:
            # Get participants and submission counts
            participants = db.query(ComputationParticipant).filter_by(computation_id=computation_id).count()
            submissions = db.query(ComputationResult).filter_by(computation_id=computation_id).count()
            
            # Determine the actual status based on submissions
            actual_status = computation.status
            if submissions >= participants and participants >= 3 and computation.status == "waiting_for_data":
                actual_status = "ready_to_compute"
            
            return {
                "status": actual_status,
                "message": "Computation is still in progress",
                "participants": participants,
                "submissions": submissions,
                "progress": f"{submissions}/{participants} organizations submitted data" if participants > 0 else "No participants yet",
                "computation_id": computation_id
            }
        
        # If completed, get the result
        result = service.get_computation_result(computation_id)
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Computation result not available"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get computation result: {str(e)}"
        )

@router.post("/computations/{computation_id}/verify")
def verify_computation(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify the integrity of a secure computation before computing the final result"""
    try:
        # Get the computation
        computation = db.query(SecureComputation).filter_by(computation_id=computation_id).first()
        if not computation:
            raise HTTPException(
                status_code=404,
                detail="Computation not found"
            )
            
        # Check if computation is in error state
        if computation.status == "error":
            return {
                "message": "Computation is in error state",
                "status": "error",
                "error_message": computation.error_message or "Unknown error occurred",
                "computation_id": computation_id
            }
            
        # Get participants and submissions with organization details
        participants = db.query(ComputationParticipant).filter_by(computation_id=computation_id).all()
        submissions = db.query(ComputationResult).filter_by(computation_id=computation_id).all()
        
        # Get submission status per organization
        submission_status = []
        for participant in participants:
            org = db.query(Organization).filter_by(id=participant.org_id).first()
            has_submitted = any(sub.org_id == participant.org_id for sub in submissions)
            submission_date = None
            
            if has_submitted:
                submission = next((sub for sub in submissions if sub.org_id == participant.org_id), None)
                submission_date = submission.created_at.isoformat() if submission and submission.created_at else None
            
            submission_status.append({
                "org_id": participant.org_id,
                "org_name": org.name if org else f"Organization {participant.org_id}",
                "has_submitted": has_submitted,
                "submitted_at": submission_date,
                "joined_at": participant.joined_at.isoformat() if participant.joined_at else None
            })
        
        # Check if we have enough submissions
        if len(submissions) < 3:  # Minimum required for privacy
            return {
                "message": f"Not enough submissions for verification. Need at least 3, got {len(submissions)}",
                "status": "waiting_for_data",
                "computation_id": computation_id,
                "submissions": len(submissions),
                "participants": len(participants),
                "submission_status": submission_status
            }
            
        # Verify the integrity of the computation based on its type
        service = SecureComputationService(db)
        verification_result = service.verify_computation_integrity(computation_id)
        
        return {
            "message": "Computation verified successfully" if verification_result["verified"] else "Verification failed",
            "status": "verified" if verification_result["verified"] else "verification_failed",
            "computation_id": computation_id,
            "details": verification_result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify computation: {str(e)}"
        )

@router.post("/computations/{computation_id}/compute")
async def compute_result(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        print(f"Starting computation for ID: {computation_id}")
        
        # First check if the computation exists and its current status
        computation = db.query(SecureComputation).filter_by(computation_id=computation_id).first()
        if not computation:
            print(f"Computation {computation_id} not found")
            raise HTTPException(
                status_code=404,
                detail="Computation not found"
            )
            
        print(f"Found computation with status: {computation.status}")
            
        # Check if computation is already completed
        if computation.status == "completed":
            return {
                "message": "Computation already completed",
                "status": "completed",
                "computation_id": computation_id
            }
            
        # Check if computation is in error state
        if computation.status == "error":
            return {
                "message": "Computation is in error state",
                "status": "error",
                "error_message": computation.error_message or "Unknown error occurred",
                "computation_id": computation_id
            }
            
        # Check if we have enough data to compute
        participants_count = db.query(ComputationParticipant).filter_by(computation_id=computation_id).count()
        submissions_count = db.query(ComputationResult).filter_by(computation_id=computation_id).count()
        
        print(f"Participants: {participants_count}, Submissions: {submissions_count}")
        
        if submissions_count == 0:
            print("No submissions found")
            return {
                "message": "No data submitted yet",
                "status": "waiting_for_data",
                "computation_id": computation_id,
                "submissions": 0,
                "participants": participants_count
            }
            
        # Perform the computation
        service = SecureComputationService(db)
        print(f"Calling perform_computation for {computation_id}")
        success = await service.perform_computation(computation_id)
        print(f"Computation result: {success}")
        
        if not success:
            # Get the updated computation to check for error message
            computation = db.query(SecureComputation).filter_by(computation_id=computation_id).first()
            print(f"Computation failed. Status: {computation.status}, Error: {computation.error_message}")
            if computation and computation.status == "error":
                return {
                    "message": "Computation failed",
                    "status": "error",
                    "error_message": computation.error_message or "Unknown error occurred",
                    "computation_id": computation_id
                }
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Computation could not be performed"
                )
                
        return {
            "message": "Successfully computed result",
            "status": "completed",
            "computation_id": computation_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute result: {str(e)}"
        )

# New endpoints for key management and secure computation protocols

@router.post("/computations/{computation_id}/client-encrypt")
def prepare_client_encryption(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Prepare encryption parameters for client-side encryption"""
    try:
        # Get the computation
        computation = db.query(SecureComputation).filter_by(computation_id=computation_id).first()
        if not computation:
            raise HTTPException(
                status_code=404,
                detail="Computation not found"
            )
            
        # Determine encryption type based on computation type
        encryption_type = "standard"
        if computation.type.startswith("secure_"):
            encryption_type = "hybrid"
        elif computation.type in ["sum", "average", "basic_statistics", "health_statistics"]:
            encryption_type = "homomorphic"
            
        # Prepare encryption parameters based on type
        if encryption_type == "homomorphic":
            # Initialize homomorphic encryption
            he = HomomorphicEncryption()
            public_key = he.get_public_key()
            
            return {
                "encryption_type": "homomorphic",
                "algorithm": "paillier",
                "public_key": public_key,
                "computation_id": computation_id
            }
        elif encryption_type == "hybrid":
            # Initialize both homomorphic encryption and SMPC
            he = HomomorphicEncryption()
            smpc = ShamirSecretSharing()
            
            public_key = he.get_public_key()
            prime = smpc.generate_prime(bits=256)
            
            # Get participants for share generation
            participants = db.query(ComputationParticipant).filter_by(computation_id=computation_id).all()
            participant_ids = [p.org_id for p in participants]
            
            return {
                "encryption_type": "hybrid",
                "homomorphic": {
                    "algorithm": "paillier",
                    "public_key": public_key
                },
                "smpc": {
                    "algorithm": "shamir_secret_sharing",
                    "threshold": 2,  # Default threshold
                    "total_shares": len(participants),
                    "prime": str(prime),
                    "participant_ids": participant_ids
                },
                "computation_id": computation_id
            }
        else:  # standard encryption
            return {
                "encryption_type": "standard",
                "algorithm": "aes",
                "computation_id": computation_id
            }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to prepare client encryption: {str(e)}"
        )

@router.get("/encryption/homomorphic/public-key")
def get_homomorphic_public_key(
    current_user: dict = Depends(get_current_user)
):
    """Get the public key for homomorphic encryption"""
    try:
        # Initialize homomorphic encryption
        he = HomomorphicEncryption()
        
        # Get the public key
        public_key = he.get_public_key()
        
        return {
            "public_key": public_key,
            "encryption_type": "homomorphic",
            "algorithm": "paillier"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get homomorphic public key: {str(e)}"
        )

@router.get("/encryption/smpc/parameters")
def get_smpc_parameters(
    threshold: int = 2,
    total_shares: int = 3,
    current_user: dict = Depends(get_current_user)
):
    """Get parameters for Shamir's Secret Sharing"""
    try:
        # Initialize SMPC protocol
        smpc = ShamirSecretSharing()
        
        # Get prime number for the field
        prime = smpc.generate_prime(bits=256)
        
        return {
            "threshold": threshold,
            "total_shares": total_shares,
            "prime": str(prime),
            "encryption_type": "smpc",
            "algorithm": "shamir_secret_sharing"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get SMPC parameters: {str(e)}"
        )

@router.get("/computations", response_model=List[Dict[str, Any]])
def list_computations(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    try:
        service = SecureComputationService(db)

        # Get user ID - handle different possible structures
        user_id_str = current_user.get("id") or current_user.get("user_id") or current_user.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=400, detail="Invalid user authentication data")

        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        computations = service.list_computations(user_id)
        
        # Enhance the computations with additional status information
        enhanced_computations = []
        for comp in computations:
            # Get participant and submission counts
            participants_count = db.query(ComputationParticipant).filter_by(computation_id=comp["computation_id"]).count()
            submissions_count = db.query(ComputationResult).filter_by(computation_id=comp["computation_id"]).count()
            
            # Calculate progress percentage
            progress_percentage = 0
            if participants_count > 0:
                progress_percentage = int((submissions_count / participants_count) * 100)
            
            # Get creator organization name - use org_id as the creator
            creator_id = comp.get("org_id")
            creator_org = db.query(Organization).filter_by(id=creator_id).first()
            
            # Handle different cases for creator name
            if creator_org and creator_org.name and creator_org.name.strip():
                creator_name = creator_org.name
            elif creator_org and creator_org.email:
                creator_name = creator_org.email
            else:
                creator_name = f"Organization {creator_id}" if creator_id else "Unknown Organization"
            
            # Add enhanced information
            enhanced_comp = {
                **comp,
                "participants_count": participants_count,
                "submissions_count": submissions_count,
                "progress_percentage": progress_percentage,
                "missing_submissions": participants_count - submissions_count if participants_count > submissions_count else 0,
                "creator_name": creator_name
            }
            
            # Add detailed status message
            if comp["status"] == "error":
                enhanced_comp["status_message"] = comp.get("error_message", "An error occurred during computation")
            elif comp["status"] == "completed":
                enhanced_comp["status_message"] = "Computation completed successfully"
            elif comp["status"] == "processing":
                enhanced_comp["status_message"] = "Computation is being processed"
            elif submissions_count == 0:
                enhanced_comp["status_message"] = "Waiting for data submissions"
            elif submissions_count < participants_count:
                enhanced_comp["status_message"] = f"Waiting for {participants_count - submissions_count} more submissions"
            else:
                enhanced_comp["status_message"] = "Ready to compute results"
                
            enhanced_computations.append(enhanced_comp)
            
        return enhanced_computations
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list computations: {str(e)}"
        )

@router.get("/computations/{computation_id}")
def get_computation_details(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Get details for a specific computation"""
    try:
        service = SecureComputationService(db)
        
        # Check if computation exists
        computation = service.get_computation(computation_id)
        
        if not computation:
            raise HTTPException(
                status_code=404,
                detail="Computation not found"
            )
        
        # Get participant and submission counts
        participants_count = db.query(ComputationParticipant).filter_by(computation_id=computation_id).count()
        # Count data submissions (stored in ComputationResult)
        submissions_count = db.query(ComputationResult).filter_by(computation_id=computation_id).count()
        
        # Calculate progress percentage
        progress_percentage = 0
        if participants_count > 0:
            progress_percentage = int((submissions_count / participants_count) * 100)
        
        # Get the computation result if available
        computation_result = None
        if computation.status == "completed":
            try:
                computation_result = service.get_computation_result(computation_id)
            except Exception as e:
                logger.error(f"Error getting computation result: {e}")
                # Don't fail the whole request if just the result is unavailable
                pass
        
        return {
            "computation_id": computation.computation_id,
            "type": computation.type,
            "status": computation.status,
            "created_at": computation.created_at.isoformat() if computation.created_at else None,
            "updated_at": computation.updated_at.isoformat() if computation.updated_at else None,
            "completed_at": computation.completed_at.isoformat() if hasattr(computation, 'completed_at') and computation.completed_at else None,
            "creator_id": computation.org_id,  # Use org_id as creator_id
            "participants_count": participants_count,
            "submissions_count": submissions_count,
            "progress_percentage": progress_percentage,
            "security_method": getattr(computation, 'security_method', 'SMPC'),
            "result": computation_result if computation_result else None,
            "error_message": computation.error_message if hasattr(computation, 'error_message') and computation.error_message else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get computation details: {str(e)}"
        )

@router.get("/computations/{computation_id}/active-participants")
async def get_active_participants(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Get active participants for a computation with submission status"""
    try:
        # Get participants
        participants = db.query(ComputationParticipant).filter_by(computation_id=computation_id).all()
        submissions = db.query(ComputationResult).filter_by(computation_id=computation_id).all()
        
        # Get organization details for each participant with submission status
        participant_details = []
        for participant in participants:
            org = db.query(Organization).filter_by(id=participant.org_id).first()
            has_submitted = any(sub.org_id == participant.org_id for sub in submissions)
            submission_date = None
            
            if has_submitted:
                submission = next((sub for sub in submissions if sub.org_id == participant.org_id), None)
                submission_date = submission.created_at.isoformat() if submission and submission.created_at else None
            
            if org:
                participant_details.append({
                    "id": participant.id,
                    "org_id": participant.org_id,
                    "organization_name": org.name,
                    "organization_type": org.type.value if org.type else "Unknown",
                    "joined_at": participant.joined_at.isoformat() if participant.joined_at else None,
                    "has_submitted": has_submitted,
                    "submitted_at": submission_date,
                    "submission_status": "submitted" if has_submitted else "pending"
                })
        
        return {
            "participants": participant_details,
            "total_count": len(participant_details),
            "submitted_count": sum(1 for p in participant_details if p["has_submitted"]),
            "pending_count": sum(1 for p in participant_details if not p["has_submitted"])
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get participants: {str(e)}"
        )

@router.get("/computations/{computation_id}/user-submission")
async def get_user_submission(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Get the user's submission for a specific computation"""
    return await _get_user_submission_internal(computation_id, current_user, db)

@router.get("/computations/{computation_id}/my-submission")
async def get_my_submission(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Get the current user's submission for a specific computation (alias for user-submission)"""
    return await _get_user_submission_internal(computation_id, current_user, db)

async def _get_user_submission_internal(
    computation_id: str,
    current_user: dict,
    db: Session
):
    """Internal function to get user submission data"""
    try:
        logger.debug(f"Fetching user submission for computation {computation_id}")
        # Get the user's organization ID
        user_org_id = current_user["id"]
        logger.debug(f"User org ID: {user_org_id}")
        
        # Check if computation exists
        computation = db.query(SecureComputation).filter_by(computation_id=computation_id).first()
        if not computation:
            logger.error(f"Computation {computation_id} not found")
            raise HTTPException(
                status_code=404,
                detail="Computation not found"
            )
        
        logger.debug(f"Found computation: {computation.computation_id}, type: {computation.type}, status: {computation.status}")
        
        # Check if user has submitted data for this computation
        submission = db.query(ComputationResult).filter_by(
            computation_id=computation_id,
            org_id=user_org_id
        ).first()
        
        if not submission:
            logger.debug(f"No submission found for user {user_org_id} in computation {computation_id}")
            
            # Also check if user is a participant but hasn't submitted yet
            participant = db.query(ComputationParticipant).filter_by(
                computation_id=computation_id,
                org_id=user_org_id
            ).first()
            
            return {
                "message": "No submission found",
                "has_submitted": False,
                "computation_id": computation_id,
                "computation_type": computation.type,
                "computation_status": computation.status,
                "is_participant": participant is not None,
                "can_submit": participant is not None or computation.org_id == user_org_id
            }
        
        logger.debug(f"Found submission for user {user_org_id} in computation {computation_id}")
        logger.debug(f"Submission data: {submission.data_points}")
        
        # Get submission details with enhanced data structure
        submission_data = {
            "has_submitted": True,
            "submitted_at": submission.created_at.isoformat() if submission.created_at else None,
            "data": submission.data_points,
            "data_points_count": len(submission.data_points) if isinstance(submission.data_points, list) else 1,
            "encryption_type": submission.encryption_type or "standard",
            "computation_id": computation_id,
            "computation_type": computation.type,
            "computation_status": computation.status,
            "org_id": user_org_id
        }
        
        logger.debug(f"Returning submission data for user {user_org_id} in computation {computation_id}: {submission_data}")
        return submission_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user submission for computation {computation_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get user submission: {str(e)}"
        )

@router.get("/computations/{computation_id}/export")
def export_computation(
    computation_id: str,
    format: str = "json",
    current_user: dict = Depends(require_permissions([Permission.VIEW_ANALYTICS])),
    db: Session = Depends(get_db)
):
    """Export a secure computation result in the specified format"""
    try:
        # Check if computation exists and user has access
        service = SecureComputationService(db)
        computation = service.get_computation(computation_id)
        
        if not computation:
            raise HTTPException(
                status_code=404,
                detail="Computation not found"
            )
        
        # Create export service
        export_service = SecureComputationExport(db)
        
        # Export the computation
        export_result = export_service.export_computation_result(computation_id, format)
        
        if "error" in export_result:
            raise HTTPException(
                status_code=400,
                detail=export_result["error"]
            )
        
        # Return the export as a downloadable file
        return Response(
            content=export_result["content"],
            media_type=export_result["content_type"],
            headers={
                "Content-Disposition": f"attachment; filename={export_result['filename']}"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export computation: {str(e)}"
        )

@router.delete("/computations/{computation_id}")
def delete_computation(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Delete a computation and all its associated data (only allowed for waiting/error computations)"""
    try:
        service = SecureComputationService(db)

        # Check if computation exists and user has permission to delete it
        computation = db.query(SecureComputation).filter_by(computation_id=computation_id).first()
        if not computation:
            raise HTTPException(
                status_code=404,
                detail="Computation not found"
            )

        # Check if user is the creator
        if computation.org_id != current_user["id"]:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to delete this computation"
            )

        # Allow deletion of computations that haven't started processing OR are in error state
        allowed_statuses = ["waiting_for_participants", "initialized", "waiting_for_data", "error"]
        if computation.status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete computation with status '{computation.status}'. Only computations that haven't started processing or are in error state can be deleted."
            )

        # Allow creator to delete computation even with participants if it's still waiting or in error
        # This gives creators full control over their computations before they start processing or when they fail

        # Delete the computation and all associated data
        success = service.delete_computation(computation_id)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to delete computation"
            )

        return {"status": "success", "message": "Computation deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete computation: {str(e)}"
        )

@router.post("/computations/{computation_id}/invite")
async def invite_participant(
    computation_id: str,
    invite_data: dict,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Invite a new participant to an existing computation"""
    try:
        org_id = invite_data.get("org_id")
        if not org_id:
            raise HTTPException(status_code=400, detail="Organization ID is required")

        user_org_id_str = current_user.get("org_id") or current_user.get("id")
        if not user_org_id_str:
            raise HTTPException(status_code=400, detail="Invalid user authentication data")

        try:
            user_org_id = int(user_org_id_str)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid user ID format")

        print(f"Inviting org_id {org_id} to computation {computation_id} by user {user_org_id}")
        
        service = SecureComputationService(db)
        result = await service.invite_participant(computation_id, org_id, user_org_id)
        return {"message": "Participant invited successfully", "result": result}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Full error details: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        logger.error(f"Error inviting participant to computation {computation_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invite participant: {str(e)}"
        )

@router.post("/computations/{computation_id}/make-public")
async def make_computation_public(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Make a computation visible to other organizations for joining"""
    try:
        service = SecureComputationService(db)
        
        # Check if computation exists and user has permission
        computation = db.query(SecureComputation).filter_by(computation_id=computation_id).first()
        if not computation:
            raise HTTPException(
                status_code=404,
                detail="Computation not found"
            )
        
        # Check if user is the creator
        if computation.org_id != current_user["id"]:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to make this computation public"
            )
        
        # Make computation public
        success = service.make_computation_public(computation_id)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to make computation public"
            )
        
        return {"status": "success", "message": "Computation is now visible to other organizations"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error making computation {computation_id} public: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to make computation public: {str(e)}"
        )

# ==========================================
# Advanced ML Capabilities Endpoints
# ==========================================

class MLTrainingRequest(BaseModel):
    model_type: str = Field(..., description="Type of ML model: 'neural_network', 'gradient_boosting', 'ensemble'")
    model_name: str = Field(..., description="Name for the model")
    task_type: str = Field(default="regression", description="Task type: 'regression' or 'classification'")
    data_type: str = Field(default="health_metrics", description="Type of data: 'health_metrics', 'clinical_data', 'genomic_data'")
    features: List[List[float]] = Field(..., description="Feature matrix for training")
    targets: List[Union[float, str]] = Field(..., description="Target values")
    privacy_params: Optional[Dict[str, Any]] = Field(default=None, description="Privacy parameters for differential privacy")
    cross_validate: bool = Field(default=False, description="Whether to perform cross-validation")

class MLPredictionRequest(BaseModel):
    model_id: str = Field(..., description="ID of the trained model")
    features: List[List[float]] = Field(..., description="Feature matrix for prediction")

class ModelDeploymentRequest(BaseModel):
    model_id: str = Field(..., description="ID of the model to deploy")
    environment: str = Field(default="development", description="Target environment: 'development', 'staging', 'production'")
    endpoint_url: Optional[str] = Field(default=None, description="Optional API endpoint for the deployed model")
    performance_thresholds: Optional[Dict[str, float]] = Field(default=None, description="Performance thresholds for monitoring")

class SecureMLComputationRequest(BaseModel):
    computation_type: str = Field(..., description="Type of computation: 'advanced_training', 'secure_prediction'")
    model_type: str = Field(..., description="Type of ML model")
    model_name: str = Field(..., description="Name for the model")
    security_method: str = Field(..., description="Security method: 'homomorphic', 'hybrid', 'standard'")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Additional parameters")

@router.post("/ml/train")
async def train_advanced_model(
    request: MLTrainingRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Train an advanced ML model with privacy guarantees."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Train the model
        result = ml_service.train_advanced_model(
            model_type=request.model_type,
            X=request.features,
            y=request.targets,
            model_name=request.model_name,
            task_type=request.task_type,
            data_type=request.data_type,
            privacy_params=request.privacy_params,
            cross_validate=request.cross_validate
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to train model")
            )

        return {
            "message": "Model trained successfully",
            "model_id": result["model_id"],
            "model_type": result["model_type"],
            "task_type": result["task_type"],
            "metrics": result.get("metrics", {}),
            "registry_id": result.get("registry_id"),
            "training_info": result.get("training_info", {})
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error training advanced model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to train model: {str(e)}"
        )

@router.post("/ml/predict")
async def predict_with_model(
    request: MLPredictionRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Make predictions using a trained ML model."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Make predictions
        result = ml_service.predict_with_advanced_model(
            model_id=request.model_id,
            X=request.features
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to make predictions")
            )

        return {
            "message": "Predictions generated successfully",
            "model_id": request.model_id,
            "predictions": result["predictions"],
            "confidence_scores": result.get("confidence_scores"),
            "prediction_count": result.get("prediction_count", len(result["predictions"]))
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error making predictions: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to make predictions: {str(e)}"
        )

@router.post("/ml/deploy")
async def deploy_model(
    request: ModelDeploymentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Deploy a trained model to a specific environment."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Deploy the model
        result = ml_service.deploy_model(
            model_id=request.model_id,
            environment=request.environment,
            deployed_by=current_user.get("id", "system"),
            endpoint_url=request.endpoint_url
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to deploy model")
            )

        return {
            "message": "Model deployed successfully",
            "deployment_id": result["deployment_id"],
            "model_id": result["model_id"],
            "environment": result["environment"],
            "status": result["status"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying model: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deploy model: {str(e)}"
        )

@router.get("/ml/models")
async def list_models(
    model_type: Optional[str] = None,
    task_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """List all trained models with optional filtering."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # List models
        models = ml_service.list_models(model_type, task_type)

        return {
            "message": "Models retrieved successfully",
            "models": models,
            "total_count": len(models)
        }

    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {str(e)}"
        )

@router.get("/ml/models/{model_id}")
async def get_model_info(
    model_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Get information about a specific trained model."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Get model info
        model_info = ml_service.get_model_info(model_id)

        if not model_info.get("success", False):
            raise HTTPException(
                status_code=404,
                detail=model_info.get("error", "Model not found")
            )

        return {
            "message": "Model information retrieved successfully",
            "model": model_info
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get model information: {str(e)}"
        )

@router.post("/ml/cross-validate")
async def cross_validate_model(
    request: MLTrainingRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Perform cross-validation on a model type."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Perform cross-validation
        result = ml_service.perform_cross_validation(
            X=request.features,
            y=request.targets,
            model_type=request.model_type,
            cv_folds=5
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to perform cross-validation")
            )

        return {
            "message": "Cross-validation completed successfully",
            "model_type": result["model_type"],
            "cv_scores": result["cv_scores"],
            "mean_score": result["mean_score"],
            "std_score": result["std_score"],
            "cv_folds": result["cv_folds"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error performing cross-validation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform cross-validation: {str(e)}"
        )

@router.get("/ml/monitoring/{deployment_id}")
async def get_model_monitoring(
    deployment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Get monitoring data for a deployed model."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Get monitoring data
        monitoring_data = ml_service.get_model_monitoring_data(deployment_id)

        if not monitoring_data.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=monitoring_data.get("error", "Failed to get monitoring data")
            )

        return {
            "message": "Monitoring data retrieved successfully",
            "deployment_id": deployment_id,
            "monitoring_data": monitoring_data["monitoring_data"],
            "performance_metrics": monitoring_data["performance_metrics"],
            "alerts": monitoring_data["alerts"],
            "alert_count": monitoring_data["alert_count"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting monitoring data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get monitoring data: {str(e)}"
        )

@router.post("/ml/monitoring/{deployment_id}/record")
async def record_prediction(
    deployment_id: str,
    prediction: Any,
    actual: Optional[Any] = None,
    latency: Optional[float] = None,
    features: Optional[List[float]] = None,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Record a model prediction for monitoring."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Record the prediction
        success = ml_service.record_model_prediction(
            deployment_id=deployment_id,
            prediction=prediction,
            actual=actual,
            latency=latency,
            features=features
        )

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to record prediction"
            )

        return {
            "message": "Prediction recorded successfully",
            "deployment_id": deployment_id,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording prediction: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record prediction: {str(e)}"
        )

@router.post("/ml/secure-computation")
async def create_secure_ml_computation(
    request: SecureMLComputationRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Create a secure computation for advanced ML training."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Create secure computation
        result = ml_service.create_secure_advanced_computation(
            computation_type=request.computation_type,
            model_type=request.model_type,
            model_name=request.model_name,
            security_method=request.security_method,
            parameters=request.parameters
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to create secure ML computation")
            )

        return {
            "message": "Secure ML computation created successfully",
            "computation_id": result["computation_id"],
            "model_name": result["model_name"],
            "model_type": result["model_type"],
            "computation_type": result["computation_type"],
            "security_method": result["security_method"],
            "status": result["status"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating secure ML computation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create secure ML computation: {str(e)}"
        )

@router.get("/ml/available-algorithms")
async def get_available_ml_algorithms(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Get information about available ML algorithms and their capabilities."""
    try:
        algorithms = {
            "neural_network": {
                "name": "Neural Network",
                "description": "Multi-layer perceptron neural network for complex pattern recognition",
                "task_types": ["regression", "classification"],
                "data_types": ["health_metrics", "clinical_data", "genomic_data"],
                "capabilities": [
                    "Deep learning",
                    "Non-linear relationships",
                    "Feature interaction learning",
                    "High-dimensional data handling"
                ],
                "use_cases": [
                    "Disease prediction",
                    "Risk stratification",
                    "Treatment outcome prediction",
                    "Medical image analysis"
                ]
            },
            "gradient_boosting": {
                "name": "Gradient Boosting",
                "description": "Ensemble learning method using decision trees",
                "task_types": ["regression", "classification"],
                "data_types": ["health_metrics", "clinical_data", "genomic_data"],
                "capabilities": [
                    "High accuracy",
                    "Feature importance",
                    "Handles missing data",
                    "Robust to outliers"
                ],
                "use_cases": [
                    "Patient outcome prediction",
                    "Readmission risk",
                    "Treatment effectiveness",
                    "Clinical decision support"
                ]
            },
            "ensemble": {
                "name": "Ensemble Methods",
                "description": "Combination of multiple models for improved performance",
                "task_types": ["regression", "classification"],
                "data_types": ["health_metrics", "clinical_data", "genomic_data"],
                "capabilities": [
                    "Improved accuracy",
                    "Reduced overfitting",
                    "Robust predictions",
                    "Model diversity"
                ],
                "use_cases": [
                    "Critical care prediction",
                    "Drug response prediction",
                    "Personalized medicine",
                    "Population health analytics"
                ]
            }
        }

        return {
            "message": "Available ML algorithms retrieved successfully",
            "algorithms": algorithms,
            "total_count": len(algorithms)
        }

    except Exception as e:
        logger.error(f"Error getting available ML algorithms: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get available ML algorithms: {str(e)}"
        )

# ==========================================
# Performance Optimization Endpoints
# ==========================================

@router.get("/performance/metrics")
async def get_performance_metrics(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Get current performance metrics and system information."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Get performance metrics
        metrics = ml_service.get_performance_metrics()

        return {
            "message": "Performance metrics retrieved successfully",
            "metrics": metrics
        }

    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance metrics: {str(e)}"
        )

@router.post("/performance/clear-cache")
async def clear_performance_cache(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Clear all cached data from the performance service."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Clear cache
        result = ml_service.clear_cache()

        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to clear cache")
            )

        return {
            "message": "Cache cleared successfully",
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )

@router.get("/performance/cache-stats")
async def get_cache_stats(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Get cache statistics from the performance service."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Get cache stats
        stats = ml_service.get_cache_stats()

        return {
            "message": "Cache statistics retrieved successfully",
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache statistics: {str(e)}"
        )

@router.post("/performance/enable-memory-efficient")
async def enable_memory_efficient_mode(
    chunk_size: int = 1000,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Enable memory-efficient processing for large datasets."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Enable memory-efficient mode
        result = ml_service.enable_memory_efficient_mode(chunk_size)

        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to enable memory-efficient mode")
            )

        return {
            "message": "Memory-efficient mode enabled successfully",
            "chunk_size": chunk_size,
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling memory-efficient mode: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enable memory-efficient mode: {str(e)}"
        )

@router.post("/performance/disable-memory-efficient")
async def disable_memory_efficient_mode(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Disable memory-efficient processing."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Disable memory-efficient mode
        result = ml_service.disable_memory_efficient_mode()

        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to disable memory-efficient mode")
            )

        return {
            "message": "Memory-efficient mode disabled successfully",
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling memory-efficient mode: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disable memory-efficient mode: {str(e)}"
        )

@router.get("/performance/system-info")
async def get_system_info(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Get system information and performance metrics."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Get system info
        info = ml_service.get_system_info()

        return {
            "message": "System information retrieved successfully",
            "system_info": info
        }

    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system information: {str(e)}"
        )

@router.post("/performance/preload-models")
async def preload_models(
    model_paths: List[str],
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Preload models into cache for faster access."""
    try:
        from services.privacy_ml_integration import PrivacyPreservingMLIntegration

        # Initialize the ML integration service
        ml_service = PrivacyPreservingMLIntegration()

        # Preload models
        result = ml_service.preload_models(model_paths)

        if not result.get("success", False):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to preload models")
            )

        return {
            "message": "Models preloaded successfully",
            "model_count": len(model_paths),
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error preloading models: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to preload models: {str(e)}"
        )
