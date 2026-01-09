from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union, Set
import csv
import io
from models import SecureComputation, ComputationParticipant, ComputationResult, Organization, ComputationInvitation, ComputationPatientRecord, DatasetDescriptor, VariableColumnMapping
from services.dataset_service import DatasetService
from services.column_mapping_service import ColumnMappingService
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
from prompt_interpreter import PromptInterpreter

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

class ComputationSpecVariable(BaseModel):
    """Generic variable specification derived from a natural-language prompt.

    This is intentionally generic so it can represent survey questions,
    clinical measurements, or derived metrics across many computation types.
    """

    # Canonical identifier used inside computations (e.g. 'fasting_glucose')
    id: Optional[str] = Field(
        default=None,
        description="Canonical variable identifier (e.g. 'fasting_glucose'). "
                    "If omitted, 'name' will be used as identifier."
    )

    # Human readable name as described by the requester
    name: str = Field(
        description="Human readable variable name as described in the prompt"
    )

    # High-level role of the variable in the study design
    role: Optional[str] = Field(
        default=None,
        description="Role in the analysis (e.g. 'exposure', 'outcome', "
                    "'covariate', 'stratifier')"
    )

    dtype: str = Field(
        default="float",
        description="Data type for this variable, e.g. 'float', 'int', 'string'"
    )

    unit: Optional[str] = Field(
        default=None,
        description="Optional unit for the variable (e.g. 'mg/dL', 'years')"
    )

    # Optional semantic tags that help map this variable to local columns
    concept_tags: Optional[List[str]] = Field(
        default=None,
        description="Optional semantic tags (e.g. ['blood_glucose', 'fasting']) "
                    "used for automatic column mapping"
    )


class ComputationSpecOperation(BaseModel):
    id: str
    type: str = Field(description="Computation type, e.g. 'secure_mean', 'secure_sum', 'secure_correlation', 'cohort_analysis'")
    input: Optional[str] = Field(default=None, description="Single input variable name for simple operations")
    x: Optional[str] = Field(default=None, description="X variable for pairwise operations like correlation")
    y: Optional[str] = Field(default=None, description="Y variable for pairwise operations like correlation")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Additional options specific to this operation (e.g. criteria for cohort analysis)")


class ComputationSpec(BaseModel):
    prompt_text: Optional[str] = Field(
        default=None,
        description="Human-readable description of the study or survey request"
    )
    research_question: Optional[str] = Field(
        default=None,
        description="Formal research question extracted from the prompt"
    )
    analysis_type: Optional[str] = Field(
        default=None,
        description="High-level analysis type inferred from the prompt "
                    "(e.g. 'mean_difference', 'regression', 'survival', 'correlation', 'basic_statistics')"
    )
    population_criteria: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Population filters (e.g. {'age_min': 18, 'age_max': 65, 'diagnosis': 'diabetes'})"
    )
    variables: List[ComputationSpecVariable] = Field(
        default_factory=list,
        description="Variables required for this computation"
    )
    operations: List[ComputationSpecOperation] = Field(
        default_factory=list,
        description="Logical operations to be performed in this computation"
    )
    output_preferences: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Output format preferences (e.g. {'include_plots': True, 'confidence_intervals': True})"
    )


class ComputationCreate(BaseModel):
    computation_type: str
    participating_orgs: List[str] = Field(default=[], description="Legacy field - use invited_org_ids instead")
    invited_org_ids: Optional[List[int]] = Field(default=None, description="List of organization IDs to invite")
    security_method: Optional[str] = Field(default="standard", description="Security method to use: 'standard', 'homomorphic', or 'hybrid'")
    threshold: Optional[int] = Field(default=2, description="Threshold for SMPC (only used with 'hybrid' security method)")
    min_participants: Optional[int] = Field(default=3, description="Minimum number of participants required for computation")
    spec: Optional[ComputationSpec] = Field(default=None, description="Optional generic computation spec capturing prompt, variables, and operations")

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


class PromptInterpretRequest(BaseModel):
    """Request body for prompt interpretation endpoint."""

    prompt_text: str


@router.post("/interpret-prompt", response_model=ComputationSpec)
def interpret_prompt(
    request: PromptInterpretRequest,
    _: dict = Depends(get_current_user),
) -> ComputationSpec:
    """Interpret a natural-language prompt into a structured computation spec.

    This endpoint is LLM-ready: if GROQ_API_KEY is configured (recommended, FREE),
    it will use Groq's fast inference; otherwise it falls back to a lightweight
    heuristic so the system keeps working in offline or restricted environments.
    """
    try:
        interpreter = PromptInterpreter()
        spec_dict = interpreter.interpret_prompt(request.prompt_text)

        # Ensure prompt_text is always present
        if not spec_dict.get("prompt_text"):
            spec_dict["prompt_text"] = request.prompt_text

        # Pydantic validation & normalization
        return ComputationSpec(**spec_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to interpret prompt: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to interpret prompt: {str(e)}",
        )

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

        # Prepare computation parameters (used by secure_average, advanced secure types, and generic spec)
        parameters: Dict[str, Any] = {}
        if computation.threshold is not None:
            parameters["threshold"] = computation.threshold

        # Attach generic computation spec if provided
        if computation.spec is not None:
            try:
                spec_dict = computation.spec.dict()
            except Exception:
                spec_dict = json.loads(computation.spec.json())
            parameters["spec"] = spec_dict

            # If this is a cohort analysis, try to propagate criteria from the spec
            if computation_type == "cohort_analysis":
                ops = spec_dict.get("operations") or []
                for op in ops:
                    op_type = op.get("type")
                    if op_type == "cohort_analysis":
                        options = op.get("options")
                        if options:
                            parameters["criteria"] = options
                        break

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
        if not file.filename or not file.filename.lower().endswith('.csv'):
            raise HTTPException(
                status_code=400,
                detail=f"Only CSV files are allowed. Received file: {file.filename or 'unknown'}"
            )
        
        # Read and parse CSV file
        try:
            content = await file.read()
            if len(content) == 0:
                raise HTTPException(status_code=400, detail="CSV file is empty")
            csv_data = content.decode('utf-8')
            if not csv_data or not csv_data.strip():
                raise HTTPException(status_code=400, detail="CSV file appears to be empty or contains no data")
        except UnicodeDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to decode CSV file. Please ensure the file is UTF-8 encoded. Error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to read CSV file: {str(e)}"
            )
        
        # Parse CSV with optional header and column selection
        data_points: Union[List[float], Dict[str, List[float]]] = []
        selected_columns: List[str] = []
        patient_rows_for_records: List[Dict[str, Any]] = []
        unique_patient_ids_for_records: Set[str] = set()
        patient_metric_column: Optional[str] = None
        patient_id_column: Optional[str] = None

        # Helper to try parse float safely
        def to_float(x: Any) -> Optional[float]:
            try:
                return float(str(x).strip())
            except Exception:
                return None

        def auto_select_columns_from_spec(
            headers: List[str],
            computation_obj: SecureComputation,
        ) -> List[str]:
            """Attempt to select relevant columns automatically using computation spec.

            This function inspects computation.parameters['spec'] (if present) and
            tries to map requested variables to the closest matching header names
            using simple string and tag similarity. It is best-effort and falls
            back to an empty list if no reasonable mapping can be found.
            """
            try:
                if not headers or not computation_obj or not computation_obj.parameters:
                    return []

                params = computation_obj.parameters or {}
                spec = params.get("spec") or {}
                variables = spec.get("variables") or []
                if not isinstance(variables, list) or not variables:
                    return []

                normalized_headers = [(h, (h or "").strip().lower()) for h in headers if h]
                if not normalized_headers:
                    return []

                auto_columns: List[str] = []

                for var in variables:
                    if not isinstance(var, dict):
                        continue
                    var_name = (var.get("name") or "").strip().lower()
                    var_id = (var.get("id") or "").strip().lower()
                    concept_tags = var.get("concept_tags") or []
                    if not isinstance(concept_tags, list):
                        concept_tags = []

                    # Build a set of tokens we will try to match in header names
                    tokens: List[str] = []
                    if var_name:
                        tokens.append(var_name)
                    if var_id:
                        tokens.append(var_id)
                    tokens.extend([str(t).strip().lower() for t in concept_tags if t])

                    if not tokens:
                        continue

                    best_header: Optional[str] = None
                    best_score = 0

                    for original, h_norm in normalized_headers:
                        score = 0
                        for tok in tokens:
                            if not tok:
                                continue
                            if tok == h_norm:
                                score += 3  # exact match
                            elif tok in h_norm:
                                score += 1  # substring match
                        if score > best_score:
                            best_score = score
                            best_header = original

                    # Require at least a minimal match
                    if best_header and best_score > 0 and best_header not in auto_columns:
                        auto_columns.append(best_header)

                return auto_columns
            except Exception as auto_err:
                logger.warning("Auto column selection from spec failed: %s", str(auto_err))
                return []

        if has_header:
            reader = csv.DictReader(io.StringIO(csv_data), delimiter=delimiter or ",")
            headers = reader.fieldnames or []
            print(f"CSV headers detected: {headers}")

            # Identify potential patient ID column (more flexible matching)
            patient_id_column = None
            for h in headers:
                if not h:
                    continue
                h_norm = h.strip().lower().replace("_", "").replace("-", "").replace(" ", "")
                # Check for various patient ID patterns
                if h_norm in ["patientid", "patientid", "pid", "id", "patient"] or "patient" in h_norm and "id" in h_norm:
                    patient_id_column = h
                    print(f"Detected patient ID column: '{h}' (normalized: '{h_norm}')")
                    break
            
            # If still not found, try first column that contains "id" (case-insensitive)
            if not patient_id_column:
                for h in headers:
                    if h and "id" in h.lower():
                        patient_id_column = h
                        print(f"Using first column with 'id' as patient ID column: '{h}'")
                        break
            
            # Last resort: use first column if no patient ID column found
            if not patient_id_column and headers:
                patient_id_column = headers[0]
                print(f"Warning: No patient ID column detected, using first column as patient ID: '{patient_id_column}'")
            
            # Check if this is a categorical filter computation (needs all columns stored)
            is_categorical_filter = False
            if computation.parameters and isinstance(computation.parameters, dict):
                spec = computation.parameters.get("spec")
                if spec and isinstance(spec, dict):
                    analysis_type = spec.get("analysis_type")
                    operations = spec.get("operations", [])
                    if analysis_type == "categorical_filter" or any(
                        op.get("type") == "categorical_filter" or 
                        (op.get("options") and op["options"].get("filters"))
                        for op in operations
                    ):
                        is_categorical_filter = True

            rows = list(reader)

            # Determine which columns to extract
            if columns:
                selected_columns = [c.strip() for c in columns.split(',') if c.strip()]
            elif column:
                selected_columns = [column.strip()]
            else:
                # Try automatic selection using computation spec (if available)
                auto_cols = auto_select_columns_from_spec(headers, computation)
                if auto_cols:
                    print(f"Auto-selected CSV columns from spec: {auto_cols}")
                    selected_columns = auto_cols
                else:
                    # Default to first header if available
                    selected_columns = headers[:1]

            # Validate columns exist
            missing = [c for c in selected_columns if c not in headers]
            if missing:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Missing columns in CSV header: {missing}. Available columns: {headers}"
                )

            if len(selected_columns) == 1:
                col = selected_columns[0]
                values: List[float] = []
                for row in rows:
                    val = to_float(row.get(col))
                    if val is not None:
                        values.append(val)

                        # Capture per-patient metric rows for secure_average or categorical_filter
                        if patient_id_column and (computation.type and computation.type.lower() == "secure_average" or is_categorical_filter):
                            pid = row.get(patient_id_column)
                            if pid is not None and str(pid).strip() != "":
                                pid_str = str(pid)
                                unique_patient_ids_for_records.add(pid_str)
                                patient_rows_for_records.append(
                                    {
                                        "patient_id": pid_str,
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

        # Helper to count numeric data points
        def _count_numeric_points(data_obj: Union[List[float], Dict[str, List[float]]]) -> int:
            if isinstance(data_obj, list):
                return len(data_obj)
            if isinstance(data_obj, dict):
                return sum(len(v) for v in data_obj.values())
            return 0

        numeric_data_points = _count_numeric_points(data_points)

        # Validate extracted data (skip for categorical filters - they store all columns separately)
        if not is_categorical_filter:
            if isinstance(data_points, list):
                if len(data_points) == 0:
                    raise HTTPException(
                        status_code=400, 
                        detail="No valid numeric values found in CSV file. Please ensure your CSV contains numeric data in the selected column(s)."
                    )
                print(f"Extracted {len(data_points)} data points from CSV (list mode): {data_points[:5]}...")
            else:
                total_vals = sum(len(v) for v in data_points.values())
                if total_vals == 0:
                    raise HTTPException(
                        status_code=400, 
                        detail=f"No valid numeric values found in selected CSV columns: {list(data_points.keys())}. Please check that the selected columns contain numeric data."
                    )
                print(f"Extracted multi-column data from CSV (dict mode): keys={list(data_points.keys())}, total_values={total_vals}")
        else:
            # For categorical filters, we'll store all columns separately, so numeric validation is not required
            print(f"Categorical filter computation detected - will store all columns from CSV")
            # Set data_points to empty dict to allow submission to proceed
            if isinstance(data_points, list) and len(data_points) == 0:
                data_points = {}
            elif isinstance(data_points, dict) and len(data_points) == 0:
                pass  # Already empty, keep it
        
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
        
        # Submit data using the service (skip for categorical filters - we store columns separately)
        if is_categorical_filter:
            # For categorical filters, we store all columns separately, so we can skip the numeric data submission
            # But we still need to mark the participant as having submitted data
            print(f"Categorical filter computation - storing all columns separately, creating minimal submission record")
            # Create a minimal ComputationResult to mark participant as having submitted
            from models import ComputationResult
            existing_result = db.query(ComputationResult).filter_by(
                computation_id=computation_id,
                org_id=user_org_id
            ).first()
            
            if existing_result:
                # Allow updating existing submission by deleting old one first
                print(f"Existing submission found for categorical filter - deleting old submission to allow update")
                # Also delete associated patient records
                db.query(ComputationPatientRecord).filter_by(
                    computation_id=computation_id,
                    org_id=user_org_id
                ).delete()
                # Delete the old submission
                db.delete(existing_result)
                db.commit()
                print(f"Deleted old submission - proceeding with new submission")
            
            # Create a minimal submission record with empty data to mark participation
            submission_record = ComputationResult(
                computation_id=computation_id,
                org_id=user_org_id,
                data_points=[],  # Empty list - data is stored in patient records
                encryption_type="standard"
            )
            db.add(submission_record)
            db.commit()
            print(f"Created minimal submission record for categorical filter computation")
            
            result = {"success": True, "message": "CSV data will be stored as patient records"}
        else:
            # Check if user already submitted - if so, allow update/replace
            from models import ComputationResult
            existing_result = db.query(ComputationResult).filter_by(
                computation_id=computation_id,
                org_id=user_org_id
            ).first()
            
            if existing_result:
                # Allow updating existing submission by deleting old one first
                print(f"Existing submission found - deleting old submission to allow update")
                # Also delete associated patient records
                db.query(ComputationPatientRecord).filter_by(
                    computation_id=computation_id,
                    org_id=user_org_id
                ).delete()
                # Delete the old submission
                db.delete(existing_result)
                db.commit()
                print(f"Deleted old submission - proceeding with new submission")
            
            # Convert dict to list if needed (for multi-column submissions)
            if isinstance(data_points, dict):
                # Flatten dict into a list of values
                flattened_points = []
                for col_name, values in data_points.items():
                    for val in values:
                        flattened_points.append({"value": val, "column": col_name})
                data_points = flattened_points
            elif not isinstance(data_points, list):
                # Ensure it's a list
                data_points = [{"value": v} for v in data_points] if data_points else []
            
            print(f"Calling service.submit_data for CSV with: computation_id={computation_id}, org_id={user_org_id}, data_points={len(data_points) if isinstance(data_points, list) else 'N/A'} items")
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
        # For categorical filter computations, also store all columns (including categorical ones)
        print(f"DEBUG: is_categorical_filter={is_categorical_filter}, has_header={has_header}, patient_id_column={patient_id_column}")
        if is_categorical_filter:
            if not has_header:
                print(f"⚠️  Warning: Categorical filter requires CSV with headers. has_header={has_header}")
            if not patient_id_column:
                print(f"⚠️  Warning: Categorical filter requires patient ID column. patient_id_column={patient_id_column}")
            
            if has_header and patient_id_column:
                try:
                    print(f"Storing patient records for categorical filter. Patient ID column: '{patient_id_column}'")
                    # Re-read CSV to get all columns
                    reader = csv.DictReader(io.StringIO(csv_data), delimiter=delimiter or ",")
                    row_count = 0
                    for row in reader:
                        row_count += 1
                        pid = row.get(patient_id_column)
                        if pid is not None and str(pid).strip() != "":
                            pid_str = str(pid)
                            unique_patient_ids_for_records.add(pid_str)
                            # Store all columns as patient records
                            for col_name, col_value in row.items():
                                if col_name == patient_id_column:
                                    continue  # Skip patient_id column itself
                                if col_value and str(col_value).strip():
                                    # Try to convert to float for numeric columns
                                    try:
                                        num_val = float(col_value)
                                        patient_rows_for_records.append({
                                            "patient_id": pid_str,
                                            "value": num_val,
                                            "metric_name": col_name,
                                        })
                                    except (ValueError, TypeError):
                                        # For categorical/string columns, store as 0.0 with value in metric_name
                                        # Format: "COLUMN_NAME:VALUE"
                                        patient_rows_for_records.append({
                                            "patient_id": pid_str,
                                            "value": 0.0,  # Placeholder for string values
                                            "metric_name": f"{col_name}:{col_value}",
                                        })
                    print(f"Processed {row_count} rows from CSV for categorical filter. Generated {len(patient_rows_for_records)} patient records.")
                except Exception as cat_err:
                    print(f"Error: Failed to store categorical columns: {cat_err}")
                    import traceback
                    traceback.print_exc()
            else:
                print(f"❌ ERROR: Cannot store patient records for categorical filter. has_header={has_header}, patient_id_column={patient_id_column}")
                if 'headers' in locals():
                    print(f"   CSV headers detected: {headers}")
                    print(f"   Available columns: {list(headers) if headers else 'N/A'}")
        
        # Persist per-patient metric records
        try:
            if patient_rows_for_records:
                records: List[ComputationPatientRecord] = []
                for row in patient_rows_for_records:
                    try:
                        patient_id = row.get("patient_id")
                        metric_name = row.get("metric_name")
                        value = row.get("value")
                        
                        if not patient_id:
                            print(f"Warning: Skipping record with missing patient_id: {row}")
                            continue
                        if not metric_name:
                            print(f"Warning: Skipping record with missing metric_name: {row}")
                            continue
                        if value is None:
                            print(f"Warning: Skipping record with None value: {row}")
                            continue
                            
                        records.append(
                            ComputationPatientRecord(
                                computation_id=computation_id,
                                org_id=user_org_id,
                                patient_id=str(patient_id),
                                metric_name=str(metric_name),
                                value=float(value) if value is not None else 0.0,
                            )
                        )
                    except Exception as rec_err:
                        print(f"Error building ComputationPatientRecord for row {row}: {rec_err}")
                        import traceback
                        traceback.print_exc()
                
                if records:
                    db.add_all(records)
                    db.commit()
                    print(f"✅ Successfully stored {len(records)} patient records for computation {computation_id}")
                    print(f"   Unique patients: {len(unique_patient_ids_for_records)}")
                    print(f"   Sample records (first 3): {records[:3] if len(records) >= 3 else records}")
                else:
                    print(f"⚠️  No patient records to store. patient_rows_for_records had {len(patient_rows_for_records)} items but none were valid.")
            else:
                if is_categorical_filter:
                    print(f"⚠️  WARNING: Categorical filter computation but no patient records were generated!")
                    print(f"   is_categorical_filter={is_categorical_filter}, has_header={has_header}, patient_id_column={patient_id_column}")
                    print(f"   patient_rows_for_records length: {len(patient_rows_for_records)}")
        except Exception as store_exc:
            # Do not fail the request if storing detailed records fails, but log the error
            print(f"❌ ERROR: Failed to store patient-level records: {store_exc}")
            import traceback
            traceback.print_exc()
        
        categorical_patient_count = len(unique_patient_ids_for_records)
        reported_data_points = numeric_data_points
        if is_categorical_filter:
            reported_data_points = max(reported_data_points, categorical_patient_count)
        
        print(f"=== CSV Submission Complete ===")
        print(f"   Data points reported: {reported_data_points}")
        print(f"   Patient records stored: {len(patient_rows_for_records)}")
        print(f"   Unique patients: {len(unique_patient_ids_for_records)}")
        print(f"   Is categorical filter: {is_categorical_filter}")
        
        return {
            "message": "CSV data submitted successfully",
            "data_points_count": reported_data_points,
            "filename": file.filename,
            "patient_records_count": len(patient_rows_for_records) if is_categorical_filter else None
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
            # Get full computation details for error state
            participants_count = db.query(ComputationParticipant).filter_by(computation_id=computation_id).count()
            submissions_count = db.query(ComputationResult).filter_by(computation_id=computation_id).count()
            
            return {
                "computation_id": computation.computation_id,
                "type": computation.type,
                "status": "error",
                "error_message": computation.error_message or "Unknown error occurred",
                "error_code": getattr(computation, 'error_code', None) or "UNKNOWN_ERROR",
                "created_at": computation.created_at.isoformat() if computation.created_at else None,
                "updated_at": computation.updated_at.isoformat() if computation.updated_at else None,
                "participants_count": participants_count,
                "submissions_count": submissions_count,
                "security_method": getattr(computation, 'security_method', 'SMPC'),
                "title": getattr(computation, 'title', None),
                "description": getattr(computation, 'description', None)
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
        
        # Add formatted result if LLM is available
        try:
            from services.result_formatter import ResultFormatter
            from fastapi.encoders import jsonable_encoder
            import copy
            
            formatter = ResultFormatter()
            spec = None
            if computation.parameters and isinstance(computation.parameters, dict):
                spec = computation.parameters.get("spec")
            research_question = None
            prompt_text = None
            if spec and isinstance(spec, dict):
                research_question = spec.get("research_question")
                prompt_text = spec.get("prompt_text")
            
            # Create a deep copy of result to avoid circular references
            result_copy = copy.deepcopy(result)
            
            # Pass the full result structure (which includes nested 'result' field)
            formatted = formatter.format_result(result_copy, spec, research_question)
            
            # Remove any potential circular references from formatted result
            # by converting to JSON and back (this breaks circular refs)
            try:
                import json
                formatted_str = json.dumps(formatted, default=str)
                formatted_clean = json.loads(formatted_str)
                result["formatted_result"] = formatted_clean
            except (TypeError, ValueError) as json_err:
                # If JSON serialization fails, try to clean manually
                logger.warning(f"Failed to clean formatted result via JSON: {json_err}")
                # Remove raw_data if it exists to avoid circular refs
                if isinstance(formatted, dict) and "raw_data" in formatted:
                    formatted_clean = {k: v for k, v in formatted.items() if k != "raw_data"}
                    result["formatted_result"] = formatted_clean
                else:
                    result["formatted_result"] = formatted
        except Exception as e:
            logger.warning(f"Failed to format result with LLM: {e}", exc_info=True)
            # Continue without formatted result
        
        # Use jsonable_encoder to ensure no circular references
        from fastapi.encoders import jsonable_encoder
        try:
            return jsonable_encoder(result)
        except Exception as enc_err:
            logger.warning(f"Failed to encode result with jsonable_encoder: {enc_err}, returning as-is")
            # Fallback: manually clean the result
            import json
            try:
                # Try to serialize and deserialize to break circular refs
                result_str = json.dumps(result, default=str)
                return json.loads(result_str)
            except (TypeError, ValueError):
                # Last resort: return basic structure
                return {
                    "computation_id": result.get("computation_id"),
                    "status": result.get("status"),
                    "result": result.get("result"),
                    "error": "Failed to serialize result due to circular references"
                }
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
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Prepare encryption parameters for client-side encryption"""
    try:
        logger.info(f"=== CLIENT ENCRYPT ENDPOINT HIT ===")
        logger.info(f"Computation ID: {computation_id}")
        logger.info(f"Current user: {current_user.get('id') if current_user else 'None'}")
        logger.info(f"User email: {current_user.get('email') if current_user else 'None'}")
        
        # Get the computation
        computation = db.query(SecureComputation).filter_by(computation_id=computation_id).first()
        if not computation:
            logger.error(f"Computation {computation_id} not found in database")
            raise HTTPException(
                status_code=404,
                detail="Computation not found"
            )
        
        logger.info(f"Found computation: type={computation.type}, status={computation.status}, security_method={computation.security_method}")
            
        # Determine encryption type based on computation type
        encryption_type = "standard"
        computation_type = computation.type or ""
        
        # Check if computation has a spec in parameters with analysis_type (for generic computations)
        spec_data = None
        if computation.parameters and isinstance(computation.parameters, dict):
            spec_data = computation.parameters.get('spec')
            if isinstance(spec_data, str):
                try:
                    spec_data = json.loads(spec_data)
                except json.JSONDecodeError:
                    spec_data = None
        
        # Determine encryption type
        if computation_type.startswith("secure_"):
            encryption_type = "hybrid"
        elif computation_type in ["sum", "average", "basic_statistics", "health_statistics", "mean_difference", "correlation", "regression"]:
            encryption_type = "homomorphic"
        elif spec_data and isinstance(spec_data, dict):
            # Check spec for analysis_type (generic prompt-driven computations)
            analysis_type = spec_data.get('analysis_type', '')
            if analysis_type in ["mean_difference", "correlation", "regression", "descriptive", "basic_statistics"]:
                encryption_type = "homomorphic"
            elif analysis_type in ["secure_mean", "secure_sum", "secure_variance"]:
                encryption_type = "hybrid"
        
        # Also check security_method if set
        if computation.security_method:
            if computation.security_method == "hybrid":
                encryption_type = "hybrid"
            elif computation.security_method == "homomorphic":
                encryption_type = "homomorphic"
            elif computation.security_method == "standard":
                encryption_type = "standard"
            
        logger.info(f"Determined encryption type: {encryption_type}")
            
        # Prepare encryption parameters based on type
        if encryption_type == "homomorphic":
            try:
                # Initialize homomorphic encryption
                he = EnhancedHomomorphicEncryption()
                public_key = he.get_public_key()
                
                logger.info("Successfully initialized homomorphic encryption")
                return {
                    "encryption_type": "homomorphic",
                    "algorithm": "paillier",
                    "public_key": public_key,
                    "computation_id": computation_id
                }
            except Exception as e:
                logger.error(f"Error initializing homomorphic encryption: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to initialize homomorphic encryption: {str(e)}"
                )
        elif encryption_type == "hybrid":
            try:
                # Initialize both homomorphic encryption and SMPC
                he = EnhancedHomomorphicEncryption()
                smpc = ShamirSecretSharing()  # Prime is automatically generated in __init__
                
                public_key = he.get_public_key()
                prime = smpc.prime  # Use the prime that was generated during initialization
                
                # Get participants for share generation
                participants = db.query(ComputationParticipant).filter_by(computation_id=computation_id).all()
                participant_ids = [p.org_id for p in participants]
                
                logger.info(f"Successfully initialized hybrid encryption with {len(participants)} participants")
                return {
                    "encryption_type": "hybrid",
                    "homomorphic": {
                        "algorithm": "paillier",
                        "public_key": public_key
                    },
                    "smpc": {
                        "algorithm": "shamir_secret_sharing",
                        "threshold": 2,  # Default threshold
                        "total_shares": len(participants) if participants else 2,
                        "prime": str(prime),
                        "participant_ids": participant_ids
                    },
                    "computation_id": computation_id
                }
            except Exception as e:
                logger.error(f"Error initializing hybrid encryption: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to initialize hybrid encryption: {str(e)}"
                )
        else:  # standard encryption
            logger.info("Using standard encryption")
            return {
                "encryption_type": "standard",
                "algorithm": "aes",
                "computation_id": computation_id
            }
    except HTTPException as he:
        logger.error(f"HTTPException in client-encrypt: status={he.status_code}, detail={he.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error preparing client encryption: {str(e)}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
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
        he = EnhancedHomomorphicEncryption()
        
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
        
        # Try to derive spec / prompt information for display
        spec = None
        prompt_text = None
        research_question = None
        try:
            if computation.parameters and isinstance(computation.parameters, dict):
                spec = computation.parameters.get("spec")
                if spec and isinstance(spec, dict):
                    prompt_text = spec.get("prompt_text")
                    research_question = spec.get("research_question")
        except Exception:
            spec = None
        
        # Get the computation result if available
        computation_result = None
        if computation.status == "completed":
            try:
                computation_result = service.get_computation_result(computation_id)
            except Exception as e:
                logger.error(f"Error getting computation result: {e}")
                # Don't fail the whole request if just the result is unavailable
                pass
        
        # Prefer stored title/description, fall back to spec prompt/research question
        title = getattr(computation, "title", None) or prompt_text or research_question
        description = getattr(computation, "description", None) or prompt_text or research_question
        
        return {
            "computation_id": computation.computation_id,
            "type": computation.type,
            "status": computation.status,
            "created_at": computation.created_at.isoformat() if computation.created_at else None,
            "updated_at": computation.updated_at.isoformat() if computation.updated_at else None,
            "completed_at": computation.completed_at.isoformat() if hasattr(computation, 'completed_at') and computation.completed_at else None,
            "creator_id": computation.org_id,  # Use org_id as creator_id
            "title": title,
            "description": description,
            "research_question": research_question,
            "participants_count": participants_count,
            "submissions_count": submissions_count,
            "progress_percentage": progress_percentage,
            "security_method": getattr(computation, 'security_method', 'SMPC'),
            "result": computation_result if computation_result else None,
            "error_message": computation.error_message if hasattr(computation, 'error_message') and computation.error_message else None,
            "error_code": computation.error_code if hasattr(computation, 'error_code') and computation.error_code else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get computation details: {str(e)}"
        )

@router.get("/{computation_id}")
def get_computation_by_id_alias(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permissions([Permission.SECURE_COMPUTATIONS]))
):
    """Alias route for /secure-computations/{id} -> handles /secure-computations/computations/{id} requests
    
    This route only matches UUID-like strings (contains hyphens) to avoid conflicts with other endpoints.
    """
    # Only process if it looks like a UUID (contains hyphens, typical UUID format)
    # This prevents conflicts with routes like /available-computations, /organizations, etc.
    if '-' not in computation_id or len(computation_id) < 30:
        raise HTTPException(
            status_code=404,
            detail="Endpoint not found"
        )
    # Call the actual handler function
    return get_computation_details(computation_id, current_user, db, _)

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
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in delete_computation endpoint: {str(e)}")
        print(f"Traceback: {error_trace}")
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


# -------------------------- Dataset Management Endpoints -------------------------- #

class DatasetCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    file_path: str
    schema: Optional[List[Dict[str, Any]]] = None


@router.post("/datasets", response_model=Dict[str, Any])
async def create_dataset(
    request: DatasetCreateRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new dataset descriptor for an organization."""
    try:
        org_id = current_user.get("id")
        if not org_id:
            raise HTTPException(status_code=401, detail="User organization not found")
        
        dataset_service = DatasetService(db)
        dataset = dataset_service.create_dataset_descriptor(
            org_id=org_id,
            name=request.name,
            file_path=request.file_path,
            description=request.description,
            schema=request.schema
        )
        
        return {
            "id": dataset.id,
            "name": dataset.name,
            "description": dataset.description,
            "schema": dataset.schema,
            "created_at": dataset.created_at.isoformat() if dataset.created_at else None
        }
    except Exception as e:
        logger.error(f"Error creating dataset: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create dataset: {str(e)}")


@router.get("/datasets", response_model=List[Dict[str, Any]])
async def list_datasets(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    active_only: bool = True
):
    """List all dataset descriptors for the current organization."""
    try:
        org_id = current_user.get("id")
        if not org_id:
            raise HTTPException(status_code=401, detail="User organization not found")
        
        dataset_service = DatasetService(db)
        datasets = dataset_service.get_dataset_descriptors(org_id=org_id, active_only=active_only)
        
        return [
            {
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "schema": d.schema,
                "created_at": d.created_at.isoformat() if d.created_at else None
            }
            for d in datasets
        ]
    except Exception as e:
        logger.error(f"Error listing datasets: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list datasets: {str(e)}")


@router.post("/datasets/infer-schema", response_model=Dict[str, Any])
async def infer_dataset_schema(
    file_path: str = Form(...),
    has_header: bool = Form(True),
    delimiter: str = Form(","),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Infer schema from a CSV file."""
    try:
        dataset_service = DatasetService(db)
        schema = dataset_service.infer_schema_from_csv(
            file_path=file_path,
            has_header=has_header,
            delimiter=delimiter
        )
        
        return {
            "schema": schema,
            "column_count": len(schema)
        }
    except Exception as e:
        logger.error(f"Error inferring schema: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to infer schema: {str(e)}")


# -------------------------- Column Mapping Endpoints -------------------------- #

class ColumnMappingRequest(BaseModel):
    computation_id: str
    dataset_id: Optional[int] = None
    dataset_columns: Optional[List[Dict[str, Any]]] = None  # Alternative to dataset_id


@router.post("/column-mapping/auto-map", response_model=Dict[str, Any])
async def auto_map_columns(
    request: ColumnMappingRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Automatically map computation variables to dataset columns."""
    try:
        org_id = current_user.get("id")
        if not org_id:
            raise HTTPException(status_code=401, detail="User organization not found")
        
        # Get computation and its spec
        computation = db.query(SecureComputation).filter(
            SecureComputation.computation_id == request.computation_id
        ).first()
        
        if not computation:
            raise HTTPException(status_code=404, detail="Computation not found")
        
        # Extract spec variables
        spec = computation.parameters.get("spec") if computation.parameters else None
        if not spec or "variables" not in spec:
            raise HTTPException(status_code=400, detail="Computation spec not found or has no variables")
        
        variables = spec["variables"]
        
        # Get dataset columns
        dataset_columns = None
        if request.dataset_id:
            dataset_service = DatasetService(db)
            dataset = dataset_service.get_dataset_by_id(request.dataset_id, org_id=org_id)
            if not dataset:
                raise HTTPException(status_code=404, detail="Dataset not found")
            dataset_columns = dataset.schema
        elif request.dataset_columns:
            dataset_columns = request.dataset_columns
        else:
            raise HTTPException(status_code=400, detail="Either dataset_id or dataset_columns must be provided")
        
        # Perform automatic mapping
        mapping_service = ColumnMappingService()
        mappings = mapping_service.auto_map_variables_to_dataset(variables, dataset_columns)
        
        # Save mappings to database (unconfirmed)
        for var_id, mapping_info in mappings.items():
            if mapping_info.get("best_match"):
                best_match = mapping_info["best_match"]
                var_mapping = VariableColumnMapping(
                    computation_id=request.computation_id,
                    org_id=org_id,
                    dataset_id=request.dataset_id,
                    variable_id=var_id,
                    column_name=best_match["column_name"],
                    confidence_score=best_match["confidence_score"],
                    mapping_method="auto",
                    confirmed=False
                )
                db.add(var_mapping)
        
        db.commit()
        
        return {
            "mappings": {
                var_id: {
                    "best_match": mapping_info.get("best_match"),
                    "all_matches": mapping_info.get("all_matches", [])
                }
                for var_id, mapping_info in mappings.items()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error auto-mapping columns: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to map columns: {str(e)}")


@router.get("/column-mapping/{computation_id}", response_model=Dict[str, Any])
async def get_column_mappings(
    computation_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get column mappings for a computation."""
    try:
        org_id = current_user.get("id")
        if not org_id:
            raise HTTPException(status_code=401, detail="User organization not found")
        
        mappings = db.query(VariableColumnMapping).filter(
            VariableColumnMapping.computation_id == computation_id,
            VariableColumnMapping.org_id == org_id
        ).all()
        
        return {
            "mappings": [
                {
                    "id": m.id,
                    "variable_id": m.variable_id,
                    "column_name": m.column_name,
                    "confidence_score": m.confidence_score,
                    "mapping_method": m.mapping_method,
                    "confirmed": m.confirmed
                }
                for m in mappings
            ]
        }
    except Exception as e:
        logger.error(f"Error getting column mappings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get mappings: {str(e)}")


@router.post("/column-mapping/confirm", response_model=Dict[str, Any])
async def confirm_column_mapping(
    mapping_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirm a column mapping."""
    try:
        org_id = current_user.get("id")
        if not org_id:
            raise HTTPException(status_code=401, detail="User organization not found")
        
        mapping = db.query(VariableColumnMapping).filter(
            VariableColumnMapping.id == mapping_id,
            VariableColumnMapping.org_id == org_id
        ).first()
        
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        mapping.confirmed = True
        db.commit()
        
        return {"message": "Mapping confirmed", "mapping_id": mapping_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming mapping: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to confirm mapping: {str(e)}")
