from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import uuid
from models import SecureComputation, ComputationParticipant, ComputationResult, Organization, ComputationInvitation, ComputationPatientRecord
from encryption_utils import EncryptionManager
from homomorphic_encryption_enhanced import EnhancedHomomorphicEncryption
from smpc_protocols import smpc_protocol
from advanced_smpc_computations import AdvancedSMPCComputations
from services.risk_stratification import RiskStratificationService
from sqlalchemy.orm import Session
import statistics
import base64
import json
import hashlib
import os
from decimal import Decimal, getcontext, InvalidOperation
from websocket import smpc_manager
import logging

# Set precision for decimal calculations
getcontext().prec = 28

logger = logging.getLogger(__name__)

class SecureComputationService:
    def __init__(self, db: Session):
        self.db = db
        self.key = hashlib.sha256(os.urandom(32)).digest()
        # Initialize encryption service as a process-wide singleton to ensure same Paillier keypair
        try:
            global _HE_SINGLETON
            if '_HE_SINGLETON' not in globals() or _HE_SINGLETON is None:
                _HE_SINGLETON = EnhancedHomomorphicEncryption(key_size=512)
                # Load persisted keypair if available; otherwise generate and persist
                try:
                    from homomorphic_encryption_enhanced import PaillierKeyPair, PaillierPublicKey, PaillierPrivateKey
                    keys_dir = os.path.join(os.path.dirname(__file__), 'keys')
                    os.makedirs(keys_dir, exist_ok=True)
                    key_path = os.path.join(keys_dir, 'paillier_keypair.json')
                    if os.path.exists(key_path):
                        with open(key_path, 'r') as f:
                            key_data = json.load(f)
                        pub = PaillierPublicKey(key_data['public']['n'], key_data['public']['g'])
                        priv = PaillierPrivateKey(key_data['private']['lambda'], key_data['private']['mu'], pub)
                        _HE_SINGLETON._key_pair = PaillierKeyPair(pub, priv)
                    else:
                        kp = _HE_SINGLETON.generate_keypair()
                        to_save = {
                            'public': kp.public_key.to_dict(),
                            'private': {
                                'lambda': kp.private_key.lambda_val,
                                'mu': kp.private_key.mu
                            }
                        }
                        with open(key_path, 'w') as f:
                            json.dump(to_save, f)
                except Exception as e:
                    # As a fallback, generate in-memory keypair
                    try:
                        _HE_SINGLETON.generate_keypair()
                    except Exception:
                        pass
            self.homomorphic_encryption = _HE_SINGLETON
        except Exception as e:
            print(f"Warning: Failed to initialize EnhancedHomomorphicEncryption singleton: {e}")
            self.homomorphic_encryption = None
        
        # Initialize advanced SMPC computations
        self.advanced_smpc = AdvancedSMPCComputations(smpc_protocol)
        
        # Make it available globally for backward compatibility
        global homomorphic_encryption
        homomorphic_encryption = self.homomorphic_encryption

    def encrypt(self, data: Any) -> Union[str, Dict[str, Any]]:
        """Encrypt data using homomorphic encryption for numeric values
        or standard encryption for other data types"""
        # For numeric data, use homomorphic encryption
        if isinstance(data, (int, float, Decimal)):
            # Always encrypt floats so HE applies its consistent scaling
            value = float(data)
            if self.homomorphic_encryption:
                return self.homomorphic_encryption.encrypt(value)
            else:
                # Fallback to basic encryption if HE is not available
                return {"encrypted": str(value), "type": "fallback"}
        
        # For lists of numeric data, encrypt each item homomorphically
        elif isinstance(data, list) and all(isinstance(x, (int, float, Decimal)) for x in data):
            if self.homomorphic_encryption:
                return [self.homomorphic_encryption.encrypt(float(x)) for x in data]
            else:
                return [{"encrypted": str(x), "type": "fallback"} for x in data]
        
        # For dictionaries with numeric values, encrypt values homomorphically
        elif isinstance(data, dict) and all(isinstance(v, (int, float, Decimal)) for v in data.values()):
            if self.homomorphic_encryption:
                return {k: self.homomorphic_encryption.encrypt(float(v)) for k, v in data.items()}
            else:
                return {k: {"encrypted": str(v), "type": "fallback"} for k, v in data.items()}
        
        # For other data types, use standard encryption
        else:
            return base64.b64encode(hashlib.sha256(data.encode() + self.key).digest()).decode()

    def decrypt(self, data: Union[str, Dict[str, Any]]) -> Any:
        """Decrypt data using homomorphic decryption for homomorphically encrypted values
        or standard decryption for other data types"""
        # For homomorphically encrypted data (dictionary format)
        if isinstance(data, dict) and 'type' in data and data.get('type') == 'paillier':
            # Expecting a JSON-friendly structure containing ciphertext and public key
            try:
                from homomorphic_encryption_enhanced import PaillierCiphertext, PaillierPublicKey
                if self.homomorphic_encryption:
                    # Accept either {'ciphertext': {...}} or flattened {'value': ..., 'public_key': {...}}
                    if 'ciphertext' in data and isinstance(data['ciphertext'], dict):
                        ct_dict = data['ciphertext']
                    else:
                        ct_dict = {k: data[k] for k in ('value', 'public_key') if k in data}
                    ciphertext = PaillierCiphertext.from_dict(ct_dict)
                    return self.homomorphic_encryption.decrypt(ciphertext)
                else:
                    # Fallback: cannot decrypt paillier without service; return 0 or raise
                    return Decimal('0')
            except Exception:
                return Decimal('0')
        
        # For fallback encrypted data
        elif isinstance(data, dict) and 'type' in data and data.get('type') == 'fallback':
            return Decimal(data.get('encrypted', '0'))
        
        # For lists of homomorphically encrypted data
        elif isinstance(data, list) and all(isinstance(x, dict) and 'type' in x for x in data):
            if self.homomorphic_encryption:
                from homomorphic_encryption_enhanced import PaillierCiphertext
                result = []
                for x in data:
                    if x.get('type') == 'paillier':
                        # Accept either wrapped or flattened dict
                        ct_dict = x['ciphertext'] if 'ciphertext' in x else {k: x[k] for k in ('value', 'public_key') if k in x}
                        try:
                            ciphertext = PaillierCiphertext.from_dict(ct_dict)
                            result.append(self.homomorphic_encryption.decrypt(ciphertext))
                        except Exception:
                            result.append(Decimal('0'))
                    else:
                        result.append(Decimal(x.get('encrypted', '0')))
                return result
            else:
                return [Decimal(x.get('encrypted', '0')) for x in data]
        
        # For dictionaries with homomorphically encrypted values
        elif isinstance(data, dict) and all(isinstance(v, dict) and 'type' in v for v in data.values()):
            if self.homomorphic_encryption:
                from homomorphic_encryption_enhanced import PaillierCiphertext
                out: Dict[str, Any] = {}
                for k, v in data.items():
                    if v.get('type') == 'paillier':
                        ct_dict = v['ciphertext'] if 'ciphertext' in v else {kk: v[kk] for kk in ('value', 'public_key') if kk in v}
                        try:
                            ciphertext = PaillierCiphertext.from_dict(ct_dict)
                            out[k] = self.homomorphic_encryption.decrypt(ciphertext)
                        except Exception:
                            out[k] = Decimal('0')
                    else:
                        out[k] = Decimal(v.get('encrypted', '0'))
                return out
            else:
                return {k: Decimal(v.get('encrypted', '0')) for k, v in data.items()}
        
        # For standard encrypted data
        else:
            # Since we're using a simple hash-based encryption in this example,
            # we can't actually decrypt. In a real implementation, you would use
            # the EncryptionManager's decrypt method.
            return base64.b64decode(data.encode()).decode() if isinstance(data, str) else data

    def create_computation(self, org_id: int, computation_type: str, make_public: bool = True, security_method: str = "homomorphic", parameters: Optional[Dict[str, Any]] = None) -> str:
        computation_id = str(uuid.uuid4())
        # Set status to waiting_for_participants if we want other orgs to see it
        initial_status = "waiting_for_participants" if make_public else "initialized"
        computation = SecureComputation(
            computation_id=computation_id,
            org_id=org_id,
            type=computation_type,
            security_method=security_method,
            status=initial_status,
            parameters=parameters
        )
        self.db.add(computation)
        self.db.commit()
        return computation_id

    def create_computation_with_invitations(self, org_id: int, computation_type: str, invited_org_ids: List[int] = None, security_method: str = "homomorphic", parameters: Optional[Dict[str, Any]] = None) -> str:
        """Create a computation and send invitations to specific organizations"""
        try:
            # Create the computation
            computation_id = self.create_computation(
                org_id,
                computation_type,
                make_public=False,
                security_method=security_method,
                parameters=parameters,
            )
            
            # Create invitations for specified organizations
            if invited_org_ids:
                for invited_org_id in invited_org_ids:
                    if invited_org_id != org_id:  # Don't invite the creator
                        invitation = ComputationInvitation(
                            computation_id=computation_id,
                            invited_org_id=invited_org_id,
                            inviter_org_id=org_id,
                            status='pending'
                        )
                        self.db.add(invitation)
                        print(f"Created invitation for org {invited_org_id} to computation {computation_id}")
                
                self.db.commit()
                print(f"Created computation {computation_id} with {len([oid for oid in invited_org_ids if oid != org_id])} invitations")
            
            return computation_id
        except Exception as e:
            print(f"Error creating computation with invitations: {e}")
            self.db.rollback()
            raise e

    def make_computation_public(self, computation_id: str) -> bool:
        """Make a computation visible to other organizations for joining"""
        try:
            computation = self.db.query(SecureComputation).filter_by(
                computation_id=computation_id
            ).first()
            
            if not computation:
                return False
                
            # Update status to make it visible to other organizations
            if computation.status == "initialized":
                computation.status = "waiting_for_participants"
                computation.updated_at = datetime.utcnow()
                self.db.commit()
                print(f"Made computation {computation_id} public")
                return True
            
            return True  # Already public or in different state
        except Exception as e:
            print(f"Error making computation public: {e}")
            self.db.rollback()
            return False

    async def get_pending_requests(self, org_id):
        """Get pending computation requests specifically targeted to this organization"""
        try:
            pending_requests = []
            
            # Find invitations specifically sent to this organization that are still pending
            expiration_date = datetime.utcnow() - timedelta(days=7)
            
            # Query for invitations where:
            # 1. This org is the invited organization
            # 2. Status is 'pending' (not accepted or declined)
            # 3. The computation is still active and not expired
            # 4. Allow computations in any status as long as invitation is pending
            invitations = self.db.query(ComputationInvitation).join(
                SecureComputation, ComputationInvitation.computation_id == SecureComputation.computation_id
            ).filter(
                ComputationInvitation.invited_org_id == org_id,
                ComputationInvitation.status == 'pending',
                SecureComputation.status.in_(["initialized", "waiting_for_participants", "waiting_for_data"]),
                SecureComputation.created_at > expiration_date
            ).all()
            
            print(f"Found {len(invitations)} targeted invitations for org {org_id}")
            
            for invitation in invitations:
                computation = invitation.computation
                
                print(f"Processing invitation for computation {computation.computation_id} from org {invitation.inviter_org_id}")
                
                # Check if org is already a participant (shouldn't happen with proper invitation management)
                existing_participant = self.db.query(ComputationParticipant).filter_by(
                    computation_id=computation.computation_id,
                    org_id=org_id
                ).first()
                
                if not existing_participant:
                    # Get inviter organization info
                    inviter_org = self.db.query(Organization).filter_by(id=invitation.inviter_org_id).first()
                    
                    pending_requests.append({
                        "computation_id": computation.computation_id,
                        "invitation_id": invitation.id,
                        "title": f"{computation.type.replace('_', ' ').title()} Computation",
                        "description": f"You have been invited to join a secure computation by {inviter_org.name if inviter_org else 'Unknown Organization'}",
                        "computation_type": computation.type,
                        "security_method": self._get_security_method(computation.type),
                        "created_at": computation.created_at.isoformat() if computation.created_at else None,
                        "invited_at": invitation.invited_at.isoformat() if invitation.invited_at else None,
                        "creator_org": inviter_org.name if inviter_org else "Unknown",
                        "status": computation.status
                    })
                    print(f"Added pending invitation from {inviter_org.name if inviter_org else 'Unknown'}")
                else:
                    print(f"Org {org_id} is already a participant in computation {computation.computation_id}")
            
            print(f"Returning {len(pending_requests)} targeted pending requests for org {org_id}")
            return pending_requests
        except Exception as e:
            print(f"Error getting pending requests: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def accept_computation_request(self, computation_id: str, user_id: int, org_id: int) -> bool:
        try:
            # Check if computation exists
            computation = self.db.query(SecureComputation).filter_by(
                computation_id=computation_id
            ).first()
            
            if not computation:
                return False
            
            # Check if there's a pending invitation for this organization
            invitation = self.db.query(ComputationInvitation).filter_by(
                computation_id=computation_id,
                invited_org_id=org_id,
                status='pending'
            ).first()
            
            if not invitation:
                print(f"No pending invitation found for org {org_id} in computation {computation_id}")
                return False
            
            # Add organization as participant
            existing_participant = self.db.query(ComputationParticipant).filter_by(
                computation_id=computation_id,
                org_id=org_id
            ).first()
            
            if not existing_participant:
                participant = ComputationParticipant(
                    computation_id=computation_id,
                    org_id=org_id
                )
                self.db.add(participant)
                
                # Update invitation status
                invitation.status = 'accepted'
                invitation.responded_at = datetime.utcnow()
                
                # Update computation status only if all invitations have been responded to
                participants_count = self.db.query(ComputationParticipant).filter_by(
                    computation_id=computation_id
                ).count() + 1  # +1 for the new participant
                
                # Check if there are any pending invitations left
                pending_invitations = self.db.query(ComputationInvitation).filter_by(
                    computation_id=computation_id,
                    status='pending'
                ).count() - 1  # -1 because we're about to mark this one as accepted
                
                # Only change status if we have enough participants AND no pending invitations
                if computation.status in ["initialized", "waiting_for_participants"] and participants_count >= 2:
                    if pending_invitations == 0:
                        # All invitations responded to, can proceed
                        computation.status = "waiting_for_data"
                        computation.updated_at = datetime.utcnow()
                        print(f"All invitations responded to, changing status to waiting_for_data")
                    else:
                        # Still have pending invitations, keep waiting
                        computation.status = "waiting_for_participants"
                        computation.updated_at = datetime.utcnow()
                        print(f"Still {pending_invitations} pending invitations, keeping status as waiting_for_participants")
                
                self.db.commit()
                print(f"Org {org_id} accepted invitation for computation {computation_id}")
            
            return True
        except Exception as e:
            print(f"Error accepting computation request: {e}")
            self.db.rollback()
            return False
    
    async def decline_computation_request(self, computation_id: str, user_id: int, org_id: int) -> bool:
        """Decline a computation request"""
        try:
            # Check if there's a pending invitation for this organization
            invitation = self.db.query(ComputationInvitation).filter_by(
                computation_id=computation_id,
                invited_org_id=org_id,
                status='pending'
            ).first()
            
            if not invitation:
                print(f"No pending invitation found for org {org_id} in computation {computation_id}")
                return False
            
            # Update invitation status to declined
            invitation.status = 'declined'
            invitation.responded_at = datetime.utcnow()
            
            # Remove any existing participant record if it exists (shouldn't exist for declined invitations)
            existing_participant = self.db.query(ComputationParticipant).filter_by(
                computation_id=computation_id,
                org_id=org_id
            ).first()
            
            if existing_participant:
                self.db.delete(existing_participant)
            
            # Check if all invitations have been responded to and update computation status
            computation = self.db.query(SecureComputation).filter_by(computation_id=computation_id).first()
            if computation:
                pending_invitations = self.db.query(ComputationInvitation).filter_by(
                    computation_id=computation_id,
                    status='pending'
                ).count() - 1  # -1 because we're about to mark this one as declined
                
                participants_count = self.db.query(ComputationParticipant).filter_by(
                    computation_id=computation_id
                ).count()
                
                # If no more pending invitations, update status based on participant count
                if pending_invitations == 0:
                    if participants_count >= 2:
                        computation.status = "waiting_for_data"
                        print(f"All invitations responded to, changing status to waiting_for_data")
                    else:
                        computation.status = "cancelled"
                        print(f"Not enough participants ({participants_count}), marking as cancelled")
                    computation.updated_at = datetime.utcnow()
            
            self.db.commit()
            print(f"Organization {org_id} declined computation request {computation_id}")
            return True
        except Exception as e:
            print(f"Error declining computation request: {e}")
            self.db.rollback()
            return False
    
    def delete_computation(self, computation_id: str) -> bool:
        """Delete a computation and all associated data"""
        try:
            print(f"=== Deleting computation {computation_id} ===")
            
            # Delete in the correct order to respect foreign key constraints
            
            # 1. Delete variable column mappings (if they exist)
            # These have a foreign key to computation_id, so must be deleted first
            try:
                from models import VariableColumnMapping
                mappings_deleted = self.db.query(VariableColumnMapping).filter_by(computation_id=computation_id).delete()
                print(f"Deleted {mappings_deleted} variable column mappings")
            except Exception as e:
                print(f"Warning: Could not delete variable column mappings (may not exist): {e}")
            
            # 2. Delete computation patient records (if they exist)
            try:
                from models import ComputationPatientRecord
                patient_records_deleted = self.db.query(ComputationPatientRecord).filter_by(computation_id=computation_id).delete()
                print(f"Deleted {patient_records_deleted} computation patient records")
            except Exception as e:
                print(f"Warning: Could not delete computation patient records (may not exist): {e}")
            
            # 3. Delete computation invitations
            invitations_deleted = self.db.query(ComputationInvitation).filter_by(computation_id=computation_id).delete()
            print(f"Deleted {invitations_deleted} invitations")
            
            # 4. Delete computation results
            results_deleted = self.db.query(ComputationResult).filter_by(computation_id=computation_id).delete()
            print(f"Deleted {results_deleted} results")
            
            # 5. Delete computation participants
            participants_deleted = self.db.query(ComputationParticipant).filter_by(computation_id=computation_id).delete()
            print(f"Deleted {participants_deleted} participants")
            
            # 6. Delete the computation itself
            computation = self.db.query(SecureComputation).filter_by(computation_id=computation_id).first()
            if computation:
                self.db.delete(computation)
                print(f"Deleted computation: {computation.computation_id}")
            else:
                print(f"Computation {computation_id} not found")
                return False
                
            self.db.commit()
            print(f"Successfully deleted computation {computation_id}")
            return True
        except Exception as e:
            self.db.rollback()
            print(f"Error deleting computation {computation_id}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def invite_participant(self, computation_id: str, org_id: int, inviter_org_id: int) -> bool:
        """Invite a new participant to an existing computation"""
        try:
            # Check if computation exists
            computation = self.db.query(SecureComputation).filter_by(computation_id=computation_id).first()
            if not computation:
                raise HTTPException(status_code=404, detail="Computation not found")
            
            # Check if inviter has permission (must be computation creator or existing participant)
            if computation.org_id != inviter_org_id:
                existing_participant = self.db.query(ComputationParticipant).filter_by(
                    computation_id=computation_id,
                    org_id=inviter_org_id
                ).first()
                if not existing_participant:
                    raise HTTPException(status_code=403, detail="You don't have permission to invite participants")
            
            # Check if organization exists
            org = self.db.query(Organization).filter_by(id=org_id).first()
            if not org:
                raise HTTPException(status_code=404, detail="Organization not found")
            
            # Check if organization is already a participant
            existing_participant = self.db.query(ComputationParticipant).filter_by(
                computation_id=computation_id,
                org_id=org_id
            ).first()
            if existing_participant:
                raise HTTPException(status_code=400, detail="Organization is already a participant")
            
            # Check if there's already a pending invitation
            existing_invitation = self.db.query(ComputationInvitation).filter_by(
                computation_id=computation_id,
                invited_org_id=org_id,
                status='pending'
            ).first()
            if existing_invitation:
                raise HTTPException(status_code=400, detail="Organization already has a pending invitation")
            
            # Create invitation instead of directly adding participant
            invitation = ComputationInvitation(
                computation_id=computation_id,
                invited_org_id=org_id,
                inviter_org_id=inviter_org_id,
                status='pending'
            )
            self.db.add(invitation)
            
            # Update computation status if needed
            if computation.status == "waiting_for_participants":
                computation.updated_at = datetime.utcnow()
            
            self.db.commit()
            print(f"Created invitation for org {org_id} to computation {computation_id} by org {inviter_org_id}")
            return True
            
        except HTTPException:
            self.db.rollback()
            raise
        except Exception as e:
            self.db.rollback()
            print(f"Error inviting participant to computation {computation_id}: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    def get_computation(self, computation_id: str):
        """Get a computation by its ID"""
        try:
            computation = self.db.query(SecureComputation).filter_by(computation_id=computation_id).first()
            return computation
        except Exception as e:
            print(f"Error getting computation: {e}")
            return None
    
    async def join_computation(self, computation_id: str, org_id: int) -> bool:
        computation = self.db.query(SecureComputation).filter_by(computation_id=computation_id).first()
        if not computation:
            return False
        
        participant = ComputationParticipant(
            computation_id=computation_id,
            org_id=org_id
        )
        self.db.add(participant)
        self.db.commit()
        
        # Get all participants for this computation
        participants = self.db.query(ComputationParticipant).filter_by(computation_id=computation_id).all()
        participant_ids = [p.org_id for p in participants]
        
        # Count submitted results
        submitted_results = self.db.query(ComputationResult).filter_by(computation_id=computation_id).count()
        
        # Notify all participants about the new join
        await smpc_manager.notify_computation_status(
            computation_id=computation_id,
            status=computation.status
        )
        
        return True

    async def submit_data(self, computation_id: str, org_id: int, data_points: List[Any]) -> Dict[str, Any]:
        """Submit data points for a secure computation using homomorphic encryption and SMPC"""
        try:
            # Check if computation exists
            computation = self.db.query(SecureComputation).filter_by(computation_id=computation_id).first()
            if not computation:
                return {
                    "success": False,
                    "error": "Computation not found",
                    "error_code": "COMPUTATION_NOT_FOUND"
                }
                
            # Check if organization is a participant
            participant = self.db.query(ComputationParticipant).filter_by(
                computation_id=computation_id, org_id=org_id
            ).first()
            
            if not participant:
                return {
                    "success": False,
                    "error": "Organization is not a participant in this computation",
                    "error_code": "NOT_A_PARTICIPANT"
                }
                
            # Check if organization already submitted data
            existing_submission = self.db.query(ComputationResult).filter_by(
                computation_id=computation_id, org_id=org_id
            ).first()
            
            if existing_submission:
                return {
                    "success": False,
                    "error": "You have already uploaded data for this computation. Each organization can only submit data once.",
                    "error_code": "ALREADY_SUBMITTED",
                    "submitted_at": existing_submission.created_at.isoformat() if existing_submission.created_at else None,
                    "data_points_count": len(existing_submission.data_points) if existing_submission.data_points else 0
                }
                
            # Enhanced validation for data points
            if not data_points or not isinstance(data_points, list):
                return {
                    "success": False,
                    "error": "Invalid data format. Expected a list of data points",
                    "error_code": "INVALID_DATA_FORMAT"
                }
            
            # Check data size limits (reasonable for college project)
            if len(data_points) > 10000:  # Limit to 10k data points
                return {
                    "success": False,
                    "error": "Too many data points. Maximum allowed: 10,000",
                    "error_code": "DATA_SIZE_LIMIT_EXCEEDED"
                }
            
            if len(data_points) < 1:
                return {
                    "success": False,
                    "error": "At least one data point is required",
                    "error_code": "INSUFFICIENT_DATA"
                }
                
            # Extract and validate numeric values for computation
            numeric_values = []
            invalid_count = 0
            
            for i, point in enumerate(data_points):
                if isinstance(point, dict) and "value" in point:
                    try:
                        # Parse as float to preserve measurement scale (mg/dL)
                        value = float(Decimal(str(point["value"])))
                        
                        # Basic range validation for health data
                        if abs(value) > 1000000:  # Reasonable upper limit
                            print(f"Warning: Very large value at index {i}: {value}")
                        
                        numeric_values.append(value)
                    except (ValueError, TypeError, InvalidOperation):
                        invalid_count += 1
                        if invalid_count <= 5:  # Log first few invalid values
                            print(f"Invalid value at index {i}: {point.get('value')}")
                elif isinstance(point, (int, float, Decimal)):
                    try:
                        # Parse as float to preserve scale
                        value = float(Decimal(str(point)))
                        
                        # Basic range validation
                        if abs(value) > 1000000:
                            print(f"Warning: Very large value at index {i}: {value}")
                            
                        numeric_values.append(value)
                    except (ValueError, TypeError, InvalidOperation):
                        invalid_count += 1
                else:
                    invalid_count += 1
                    
            # Report validation results
            if invalid_count > 0:
                print(f"Skipped {invalid_count} invalid data points out of {len(data_points)}")
                    
            if not numeric_values:
                return {
                    "success": False,
                    "error": f"No valid numeric data points found. Skipped {invalid_count} invalid values.",
                    "error_code": "NO_VALID_DATA"
                }
            
            # Check if we have enough valid data
            if len(numeric_values) < len(data_points) * 0.5:  # At least 50% should be valid
                return {
                    "success": False,
                    "error": f"Too many invalid data points. Only {len(numeric_values)} out of {len(data_points)} are valid.",
                    "error_code": "HIGH_INVALID_DATA_RATE"
                }
                
            # Determine the computation type and apply appropriate secure method
            computation_type = computation.type.lower()
            
            # Log one sample pre-encryption value for sanity
            try:
                print(f"Sample value before encryption: {numeric_values[0]}")
            except Exception:
                pass

            # Apply homomorphic encryption to the data points (as floats)
            encrypted_values = []
            for value in numeric_values:
                try:
                    # Use homomorphic encryption for numeric values
                    if self.homomorphic_encryption:
                        # Debug: log first few raw values before encryption
                        try:
                            if idx < 5:
                                print(f"[SUBMIT DEBUG] raw_value_before_encrypt[{idx}]={float(value)}")
                        except Exception:
                            pass
                        encrypted_value = self.homomorphic_encryption.encrypt(float(value))
                    else:
                        # Fallback encryption
                        encrypted_value = {"encrypted": str(float(value)), "type": "fallback"}
                    encrypted_values.append(encrypted_value)
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Error encrypting data: {str(e)}",
                        "error_code": "ENCRYPTION_ERROR"
                    }

            # Serialize encrypted values to JSON-friendly structures
            serialized_encrypted_values: List[Dict[str, Any]] = []
            try:
                from homomorphic_encryption_enhanced import PaillierCiphertext
                for ev in encrypted_values:
                    if isinstance(ev, dict):
                        # Already a serializable fallback structure
                        serialized_encrypted_values.append(ev)
                    elif isinstance(ev, PaillierCiphertext):
                        serialized_encrypted_values.append({
                            "type": "paillier",
                            "ciphertext": ev.to_dict(),
                        })
                    else:
                        # Unknown type; best-effort string representation
                        serialized_encrypted_values.append({
                            "type": "unknown",
                            "value": str(ev),
                        })
            except Exception:
                # If import fails, fallback to stringifying values
                serialized_encrypted_values = [ev if isinstance(ev, dict) else {"type": "unknown", "value": str(ev)} for ev in encrypted_values]
            
            # For certain computation types, we might want to use SMPC instead
            # of or in addition to homomorphic encryption
            if computation_type in ["secure_sum", "secure_mean", "secure_variance", "secure_average", "secure_correlation"]:
                # Generate SMPC shares for each value
                smpc_shares = []
                for value in numeric_values:
                    try:
                        # Generate shares using Shamir's Secret Sharing
                        # SMPC operates on integers; use rounded value
                        shares = smpc_protocol.generate_shares(int(round(value)), 3, 2)  # t=2, n=3
                        smpc_shares.append(shares)
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"Error generating SMPC shares: {str(e)}",
                            "error_code": "SMPC_ERROR"
                        }
                
                # Store both homomorphic encrypted values and SMPC shares
                submission_data = {
                    "homomorphic": serialized_encrypted_values,
                    "smpc_shares": smpc_shares,
                    "original_count": len(numeric_values)
                }
            else:
                # For other computation types, just use homomorphic encryption
                submission_data = serialized_encrypted_values
                
            # Create a new submission
            result = ComputationResult(
                computation_id=computation_id,
                org_id=org_id,
                data_points=submission_data
            )
            
            self.db.add(result)
            self.db.commit()
            
            # Update computation status if needed
            if computation.status == "initialized":
                computation.status = "waiting_for_data"
                computation.updated_at = datetime.utcnow()
                self.db.commit()
            
            # Get updated participant and submission counts
            participants = self.db.query(ComputationParticipant).filter_by(computation_id=computation_id).all()
            participant_ids = [p.org_id for p in participants]
            submitted_results = self.db.query(ComputationResult).filter_by(computation_id=computation_id).count()
            
            # Notify all participants about the data submission
            await smpc_manager.notify_data_submitted(
                computation_id=computation_id,
                org_id=org_id
            )
            
            # Update computation status for all participants
            await smpc_manager.notify_computation_status(
                computation_id=computation_id,
                status=computation.status
            )
                
            return {
                "success": True,
                "message": "Data submitted successfully",
                "data_points_count": len(numeric_values),
                "encryption_type": "homomorphic" if computation_type not in ["secure_sum", "secure_mean", "secure_variance", "secure_average", "secure_correlation"] else "hybrid"
            }
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "error": f"Error submitting data: {str(e)}",
                "error_code": "SUBMISSION_ERROR"
            }

    def get_computation_result(self, computation_id: str, org_id: Optional[int] = None) -> Dict[str, Any]:
        computation = self.db.query(SecureComputation).filter_by(computation_id=computation_id).first()
        if not computation:
            return None
            
        # Create a base response with computation details
        response = {
            "computation_id": computation.computation_id,
            "type": computation.type,
            "status": computation.status,
            "created_at": computation.created_at.isoformat(),
            "updated_at": computation.updated_at.isoformat() if computation.updated_at else None,
            "completed_at": computation.completed_at.isoformat() if computation.completed_at else None,
            "security_method": self._get_security_method(computation.type)
        }
        # Attach generic computation spec if present in parameters
        try:
            if computation.parameters and isinstance(computation.parameters, dict):
                spec = computation.parameters.get("spec")
                if spec is not None:
                    response["spec"] = spec
        except Exception:
            # Do not fail result retrieval if parameters are malformed
            pass
        
        # Add error information if in error state
        if computation.status == "error":
            response["error_message"] = computation.error_message
            response["error_code"] = computation.error_code
            return response
            
        # Add result information if completed
        if computation.status == "completed" and computation.result:
            response["result"] = computation.result
            return response
            
        # Add progress information if still in progress
        if computation.status in ["initialized", "processing", "waiting_for_data"]:
            # Get participants and submission counts
            participants = self.db.query(ComputationParticipant).filter_by(computation_id=computation_id).all()
            submissions = self.db.query(ComputationResult).filter_by(computation_id=computation_id).all()
            
            participant_ids = {p.org_id for p in participants}
            submission_ids = {s.org_id for s in submissions}
            missing_ids = participant_ids - submission_ids
            
            response["participants_count"] = len(participants)
            response["submissions_count"] = len(submissions)
            response["missing_count"] = len(missing_ids)
            response["progress_percentage"] = int((len(submissions) / len(participants)) * 100) if participants else 0
            
            if missing_ids:
                response["missing_organizations"] = list(missing_ids)
            
            # Add organization-specific submission info if org_id is provided
            if org_id is not None:
                org_submission = self.db.query(ComputationResult).filter_by(
                    computation_id=computation_id,
                    org_id=org_id
                ).first()
                
                if org_submission:
                    # Determine data points count based on submission format
                    data_points_count = 0
                    if isinstance(org_submission.data_points, list):
                        data_points_count = len(org_submission.data_points)
                    elif isinstance(org_submission.data_points, dict):
                        if "homomorphic" in org_submission.data_points:
                            data_points_count = len(org_submission.data_points["homomorphic"])
                        elif "smpc_shares" in org_submission.data_points:
                            data_points_count = org_submission.data_points.get("original_count", 0)
                        else:
                            data_points_count = 1
                    else:
                        data_points_count = 1
                        
                    response["your_submission"] = {
                        "submitted_at": org_submission.created_at.isoformat() if org_submission.created_at else None,
                        "data_points_count": data_points_count,
                        "encryption_type": self._determine_encryption_type(org_submission.data_points)
                    }
                
        return response
        
    def _get_security_method(self, computation_type: str) -> str:
        """Determine the security method used for a computation type
        
        Args:
            computation_type: The type of computation
            
        Returns:
            String describing the security method
        """
        computation_type = computation_type.lower()
        
        # Advanced SMPC computations (require hybrid security)
        advanced_smpc_types = [
            "secure_sum", "secure_mean", "secure_variance", "secure_average",
            "secure_correlation", "secure_regression", "secure_survival",
            "federated_logistic", "federated_random_forest", "anomaly_detection",
            "cohort_analysis", "drug_safety", "epidemiological",
            "secure_gwas", "pharmacogenomics"
        ]
        
        if computation_type in advanced_smpc_types:
            return "hybrid (homomorphic encryption + SMPC)"
        elif computation_type in ["sum", "average", "basic_statistics", "health_statistics"]:
            return "homomorphic encryption"
        else:
            return "standard encryption"
    
    def _determine_encryption_type(self, data_points: Any) -> str:
        """Determine the encryption type used for data points
        
        Args:
            data_points: The data points to check
            
        Returns:
            String describing the encryption type
        """
        if isinstance(data_points, dict):
            if "homomorphic" in data_points:
                return "homomorphic"
            elif "smpc_shares" in data_points:
                return "smpc"
            else:
                # Try to check the first item if it's a dictionary with type field
                for key, value in data_points.items():
                    if isinstance(value, dict) and "type" in value:
                        if value["type"] == "paillier":
                            return "homomorphic"
                        elif value["type"] == "rsa":
                            return "standard"
                return "standard"
        elif isinstance(data_points, list) and data_points:
            # Check if items are homomorphically encrypted
            if isinstance(data_points[0], dict) and "type" in data_points[0] and data_points[0].get("type") == "paillier":
                return "homomorphic"
        return "standard"
        
    def verify_computation_integrity(self, computation_id: str) -> Dict[str, Any]:
        """Verify the integrity of a secure computation before computing the final result"""
        # Get the computation
        computation = self.db.query(SecureComputation).filter_by(computation_id=computation_id).first()
        if not computation:
            return {
                "verified": False,
                "error": "Computation not found"
            }
            
        # Check if computation is in error state
        if computation.status == "error":
            return {
                "verified": False,
                "error": computation.error_message or "Unknown error occurred"
            }
            
        # Get participants and submissions
        participants = self.db.query(ComputationParticipant).filter_by(computation_id=computation_id).all()
        submissions = self.db.query(ComputationResult).filter_by(computation_id=computation_id).all()
        
        # Check if we have enough submissions
        if len(submissions) < 3:  # Minimum required for privacy
            return {
                "verified": False,
                "error": f"Not enough submissions for verification. Need at least 3, got {len(submissions)}",
                "submissions_count": len(submissions),
                "participants_count": len(participants)
            }
            
        # Determine security method based on computation type
        security_method = self._get_security_method(computation.type)
        
        # Verify based on security method
        if "hybrid" in security_method:
            return self._verify_hybrid_computation(computation_id, submissions)
        elif "homomorphic" in security_method:
            return self._verify_homomorphic_computation(computation_id, submissions)
        else:  # standard
            return self._verify_standard_computation(computation_id, submissions)
            
    def _verify_standard_computation(self, computation_id: str, submissions: List[ComputationResult]) -> Dict[str, Any]:
        """Verify integrity of standard computation"""
        # For standard computation, just check that all submissions have valid data
        for submission in submissions:
            if not submission.data_points:
                return {
                    "verified": False,
                    "error": f"Invalid data format in submission from org {submission.org_id}"
                }
                
        return {
            "verified": True,
            "security_method": "standard",
            "submissions_verified": len(submissions)
        }
        
    def _verify_homomorphic_computation(self, computation_id: str, submissions: List[ComputationResult]) -> Dict[str, Any]:
        """Verify integrity of homomorphic computation"""
        # For homomorphic computation, verify that all submissions have valid homomorphic encrypted data
        for submission in submissions:
            if not submission.data_points:
                return {
                    "verified": False,
                    "error": f"Invalid data format in submission from org {submission.org_id}"
                }
                
            # Check for homomorphic encryption format
            encryption_type = self._determine_encryption_type(submission.data_points)
            if encryption_type != "homomorphic":
                return {
                    "verified": False,
                    "error": f"Expected homomorphic encryption, but found {encryption_type} in submission from org {submission.org_id}"
                }
                
        return {
            "verified": True,
            "security_method": "homomorphic",
            "encryption_type": "homomorphic",
            "submissions_verified": len(submissions)
        }
        
    def _verify_hybrid_computation(self, computation_id: str, submissions: List[ComputationResult]) -> Dict[str, Any]:
        """Verify integrity of hybrid computation (homomorphic + SMPC)"""
        # For hybrid computation, verify both homomorphic and SMPC components
        homomorphic_verified = True
        smpc_verified = True
        errors = []
        
        for submission in submissions:
            if not submission.data_points or not isinstance(submission.data_points, dict):
                return {
                    "verified": False,
                    "error": f"Invalid data format in submission from org {submission.org_id}"
                }
                
            # Check for homomorphic encryption
            if "homomorphic" not in submission.data_points:
                homomorphic_verified = False
                errors.append(f"Missing homomorphic encryption data in submission from org {submission.org_id}")
            
            # Check for SMPC shares
            if "smpc_shares" not in submission.data_points:
                smpc_verified = False
                errors.append(f"Missing SMPC shares in submission from org {submission.org_id}")
                    
        verified = homomorphic_verified and smpc_verified
        
        return {
            "verified": verified,
            "security_method": "hybrid",
            "homomorphic_verified": homomorphic_verified,
            "smpc_verified": smpc_verified,
            "encryption_types": ["homomorphic", "smpc"],
            "submissions_verified": len(submissions),
            "errors": errors if errors else None
        }

    async def perform_computation(self, computation_id: str) -> bool:
        try:
            computation = self.db.query(SecureComputation).filter_by(computation_id=computation_id).first()
            if not computation:
                raise ValueError("Computation not found")
            
            # Check if computation is already in error state
            if computation.status == "error":
                # Already in error state, no need to process again
                return False
                
            # Check if computation is already completed
            if computation.status == "completed":
                return True
                
            # Update status to processing
            computation.status = "processing"
            computation.updated_at = datetime.utcnow()
            self.db.commit()
            
            results = self.db.query(ComputationResult).filter_by(computation_id=computation_id).all()
            if not results:
                computation.status = "error"
                computation.error_message = "No data submitted for computation"
                computation.error_code = "NO_DATA_SUBMITTED"
                computation.updated_at = datetime.utcnow()
                self.db.commit()
                return False
            
            # Get all participants for this computation
            participants = self.db.query(ComputationParticipant).filter_by(computation_id=computation_id).all()
            if not participants:
                computation.status = "error"
                computation.error_message = "No participants found for computation"
                computation.error_code = "NO_PARTICIPANTS"
                computation.updated_at = datetime.utcnow()
                self.db.commit()
                return False
                
            # Check if all participants have submitted data
            participant_ids = {p.org_id for p in participants}
            submission_ids = {r.org_id for r in results}
            missing_submissions = participant_ids - submission_ids
            
            # Check minimum submissions requirement (relaxed for testing)
            min_required = 1  # Reduced to 1 for testing single-org computations
            if len(results) < min_required:
                computation.status = "waiting_for_data"
                computation.error_message = f"Waiting for more submissions. Only {len(results)} of {len(participants)} participants have submitted data. Need at least {min_required}."
                computation.error_code = "INSUFFICIENT_SUBMISSIONS"
                computation.updated_at = datetime.utcnow()
                self.db.commit()
                print(f"Insufficient submissions: {len(results)} < {min_required}")
                return False
            
            # Determine computation type and use appropriate secure method
            computation_type = computation.type.lower()
            
            # Define advanced SMPC computation types (same as in _determine_security_method)
            advanced_smpc_types = [
                "secure_sum", "secure_mean", "secure_variance", "secure_average",
                "secure_correlation", "secure_regression", "secure_survival",
                "federated_logistic", "federated_random_forest", "anomaly_detection",
                "cohort_analysis", "drug_safety", "epidemiological",
                "secure_gwas", "pharmacogenomics"
            ]
            
            # Check if computation has a spec (generic prompt-driven)
            spec = None
            if computation.parameters and isinstance(computation.parameters, dict):
                spec = computation.parameters.get("spec")
            
            # Process data based on computation type or spec
            try:
                if spec and spec.get("operations"):
                    # Use spec-based execution (generic prompt-driven)
                    print(f"Processing computation using spec-based execution")
                    result = self._perform_spec_based_computation(computation, results, spec)
                else:
                    # Legacy: use computation type
                    print(f"Processing computation type: {computation_type}")
                    if computation_type in advanced_smpc_types:
                        # These types use both homomorphic encryption and SMPC (hybrid)
                        print("Using hybrid computation method")
                        result = self._perform_secure_computation_hybrid(computation, results)
                    else:
                        # Other types use homomorphic encryption only
                        print("Using homomorphic computation method")
                        result = self._perform_secure_computation_homomorphic(computation_type, results)
                
                # Add metadata about the computation
                result["data_points_count"] = result.get("count", 0)
                result["organizations_count"] = len(set(r.org_id for r in results))
                result["computation_type"] = computation.type
                result["timestamp"] = datetime.utcnow().isoformat()
                result["secure_computation_method"] = "hybrid" if computation_type in advanced_smpc_types else "homomorphic"
                
                # Update computation with results
                computation.result = result
                computation.status = "completed"
                computation.completed_at = datetime.utcnow()
                computation.updated_at = datetime.utcnow()
                self.db.commit()
                
                # Get participants for notification
                participants = self.db.query(ComputationParticipant).filter_by(computation_id=computation_id).all()
                participant_ids = [p.org_id for p in participants]
                
                # Notify all participants about computation completion
                await smpc_manager.notify_computation_completed(
                    computation_id=computation_id,
                    result={
                        "status": "completed",
                        "data_points_count": result.get("data_points_count", 0),
                        "organizations_count": result.get("organizations_count", 0),
                        "computation_type": computation.type,
                        "secure_method": result.get("secure_computation_method", "homomorphic")
                    }
                )
                
                # Update computation status for all participants
                await smpc_manager.notify_computation_status(
                    computation_id=computation_id,
                    status=computation.status
                )
                
                return True
            except Exception as e:
                print(f"Computation error: {str(e)}")
                import traceback
                traceback.print_exc()
                computation.status = "error"
                computation.error_message = f"Error calculating statistics: {str(e)}"
                computation.error_code = "GENERAL_CALCULATION_ERROR"
                computation.updated_at = datetime.utcnow()
                self.db.commit()
                return False
        except Exception as e:
            # Catch any other exceptions
            try:
                if computation:
                    computation.status = "error"
                    computation.error_message = f"Computation failed: {str(e)}"
                    self.db.commit()
            except:
                pass
            return False
            
    def _perform_secure_computation_hybrid(self, computation: SecureComputation, results: List[ComputationResult]) -> Dict[str, Any]:
        """Perform secure computation using both homomorphic encryption and SMPC"""

        computation_type = computation.type.lower()
        parameters: Dict[str, Any] = computation.parameters or {}

        # Check if this is an advanced computation type that requires SMPC
        advanced_computations = self.advanced_smpc.get_available_computations()
        if computation_type in advanced_computations:
            return self._perform_advanced_computation(computation, results)

        # For basic computations (secure_sum, secure_mean, secure_average, secure_variance),
        # use homomorphic encryption data instead of SMPC shares
        # Extract homomorphic encrypted data from results
        all_encrypted_data = []
        for result in results:
            # Handle both formats: direct list of encrypted values or dict with "homomorphic" key
            if isinstance(result.data_points, dict) and "homomorphic" in result.data_points:
                all_encrypted_data.extend(result.data_points["homomorphic"])
            elif isinstance(result.data_points, list):
                all_encrypted_data.extend(result.data_points)

        if not all_encrypted_data:
            raise ValueError("No valid encrypted data found in submissions")

        # Process based on computation type using homomorphic encryption
        result = {}

        # Count is always available
        result["count"] = len(all_encrypted_data)

        if computation_type == "secure_sum":
            # For sum, use homomorphic addition via HE helper when available
            if self.homomorphic_encryption:
                try:
                    from homomorphic_encryption_enhanced import PaillierCiphertext
                    ciphertexts = []
                    for enc_val in all_encrypted_data:
                        if isinstance(enc_val, dict) and enc_val.get('type') == 'paillier':
                            ct_dict = enc_val['ciphertext'] if 'ciphertext' in enc_val else {k: enc_val[k] for k in ('value', 'public_key') if k in enc_val}
                            ciphertexts.append(PaillierCiphertext.from_dict(ct_dict))
                        else:
                            ciphertexts = None
                            break
                    if ciphertexts is not None and ciphertexts:
                        # Ensure all ciphertexts share the same public key
                        try:
                            same_key = len({ct.public_key.n for ct in ciphertexts}) == 1
                        except Exception:
                            same_key = False
                        if not same_key:
                            ciphertexts = None
                    if ciphertexts is not None and ciphertexts:
                        # Debug: decrypt a small sample to verify scale
                        try:
                            sample_dec = []
                            for ct in ciphertexts[:5]:
                                sample_dec.append(float(self.homomorphic_encryption.decrypt(ct)))
                            print(f"[HYBRID DEBUG] secure_sum: sample_dec_first5={sample_dec} count={len(ciphertexts)}")
                        except Exception as _e:
                            print(f"[HYBRID DEBUG] secure_sum: sample decrypt failed: {_e}")
                        encrypted_sum = self.homomorphic_encryption.secure_sum(ciphertexts)
                        # Decrypt the final sum
                        dec_sum = float(self.homomorphic_encryption.decrypt(encrypted_sum))
                        print(f"[HYBRID DEBUG] secure_sum: dec_sum={dec_sum}")
                        result["sum"] = dec_sum
                    else:
                        # Fallback: decrypt and sum manually
                        decrypted_values = []
                        for enc_val in all_encrypted_data:
                            if isinstance(enc_val, dict) and enc_val.get('type') == 'fallback':
                                decrypted_values.append(float(enc_val.get('encrypted', '0')))
                            else:
                                decrypted_values.append(float(self.decrypt(enc_val)))
                        result["sum"] = sum(decrypted_values)
                except Exception:
                    # Fallback on error
                    decrypted_values = []
                    for enc_val in all_encrypted_data:
                        if isinstance(enc_val, dict) and enc_val.get('type') == 'fallback':
                            decrypted_values.append(float(enc_val.get('encrypted', '0')))
                        else:
                            decrypted_values.append(float(self.decrypt(enc_val)))
                    result["sum"] = sum(decrypted_values)
            else:
                # Fallback: decrypt and sum manually
                decrypted_values = []
                for enc_val in all_encrypted_data:
                    if isinstance(enc_val, dict) and enc_val.get('type') == 'fallback':
                        decrypted_values.append(float(enc_val.get('encrypted', '0')))
                    else:
                        decrypted_values.append(float(enc_val))
                result["sum"] = sum(decrypted_values)

        elif computation_type in ["secure_mean", "secure_average"]:
            # For mean/average, use homomorphic addition then divide
            if self.homomorphic_encryption:
                # Reconstruct Paillier ciphertexts from JSON-friendly dicts
                try:
                    from homomorphic_encryption_enhanced import PaillierCiphertext
                    ciphertexts = []
                    for enc_val in all_encrypted_data:
                        if isinstance(enc_val, dict) and enc_val.get('type') == 'paillier':
                            ct_dict = enc_val['ciphertext'] if 'ciphertext' in enc_val else {k: enc_val[k] for k in ('value', 'public_key') if k in enc_val}
                            ciphertexts.append(PaillierCiphertext.from_dict(ct_dict))
                        else:
                            # If not paillier (e.g., fallback), skip to fallback path
                            ciphertexts = None
                            break
                    if ciphertexts is not None and ciphertexts:
                        # Ensure all ciphertexts share the same public key (same modulus n)
                        try:
                            same_key = len({ct.public_key.n for ct in ciphertexts}) == 1
                        except Exception:
                            same_key = False
                        if not same_key:
                            ciphertexts = None
                    if ciphertexts is not None and ciphertexts:
                        # Debug: decrypt a small sample to verify scale
                        try:
                            sample_dec = []
                            for ct in ciphertexts[:5]:
                                sample_dec.append(float(self.homomorphic_encryption.decrypt(ct)))
                            print(f"[HYBRID DEBUG] secure_avg: sample_dec_first5={sample_dec} count={len(ciphertexts)}")
                        except Exception as _e:
                            print(f"[HYBRID DEBUG] secure_avg: sample decrypt failed: {_e}")
                        encrypted_sum = self.homomorphic_encryption.secure_sum(ciphertexts)
                        # Decrypt and divide by count
                        sum_value = self.homomorphic_encryption.decrypt(encrypted_sum)
                        print(f"[HYBRID DEBUG] secure_avg: dec_sum={float(sum_value)} divisor={len(all_encrypted_data)}")
                        result["mean"] = float(sum_value) / len(all_encrypted_data)
                        result["average"] = result["mean"]  # Add average alias
                    else:
                        # Fallback: decrypt and calculate average manually
                        decrypted_values = []
                        for enc_val in all_encrypted_data:
                            if isinstance(enc_val, dict) and enc_val.get('type') == 'fallback':
                                decrypted_values.append(float(enc_val.get('encrypted', '0')))
                            else:
                                decrypted_values.append(float(self.decrypt(enc_val)))
                        result["mean"] = sum(decrypted_values) / len(decrypted_values) if decrypted_values else 0
                        result["average"] = result["mean"]
                except Exception:
                    # As a safety net, fall back to decrypting values then averaging
                    decrypted_values = []
                    for enc_val in all_encrypted_data:
                        if isinstance(enc_val, dict) and enc_val.get('type') == 'fallback':
                            decrypted_values.append(float(enc_val.get('encrypted', '0')))
                        else:
                            decrypted_values.append(float(self.decrypt(enc_val)))
                    result["mean"] = sum(decrypted_values) / len(decrypted_values) if decrypted_values else 0
                    result["average"] = result["mean"]

            else:
                # Fallback: decrypt and calculate average manually
                decrypted_values = []
                for enc_val in all_encrypted_data:
                    if isinstance(enc_val, dict) and enc_val.get('type') == 'fallback':
                        decrypted_values.append(float(enc_val.get('encrypted', '0')))
                    else:
                        decrypted_values.append(float(enc_val))
                result["mean"] = sum(decrypted_values) / len(decrypted_values) if decrypted_values else 0
                result["average"] = result["mean"]

            # Threshold-based analysis and risk stratification specifically for secure_average
            if computation_type == "secure_average":
                threshold_value = parameters.get("threshold")
                metric_name = parameters.get("metric", "blood_sugar")

                patient_records: List[ComputationPatientRecord] = []
                try:
                    patient_records = self.db.query(ComputationPatientRecord).filter_by(
                        computation_id=computation.computation_id
                    ).all()
                except Exception:
                    patient_records = []

                if patient_records:
                    values = [float(r.value) for r in patient_records if r.value is not None]
                    if values:
                        result["metric_name"] = metric_name
                        result["patient_records_count"] = len(values)

                        # Threshold-based counts and list of impacted patients
                        # Generate a list of all patients with their risk levels and threshold status
                        all_patient_records = []
                        for record in patient_records:
                            all_patient_records.append({
                                "patient_id": record.patient_id,
                                "value": float(record.value) if record.value is not None else None,
                                "risk_level": "unknown",
                                "above_threshold": False,
                                "consequences": None,
                            })

                        # Threshold-based counts
                        threshold_float: Optional[float] = None
                        if threshold_value is not None:
                            try:
                                threshold_float = float(threshold_value)
                            except (TypeError, ValueError):
                                threshold_float = None

                        if threshold_float is not None:
                            above_records = [
                                p for p in all_patient_records
                                if p["value"] is not None and float(p["value"]) >= threshold_float
                            ]
                            result["threshold_value"] = threshold_float
                            result["above_threshold_count"] = len(above_records)
                            result["above_threshold_percentage"] = (
                                (len(above_records) / len(all_patient_records)) * 100.0
                            )

                        # Build per-patient list with risk level classification
                        try:
                            risk_service = RiskStratificationService()

                            thresholds_cfg = None
                            for key, cfg in risk_service.risk_thresholds.items():
                                if key in metric_name.lower():
                                    thresholds_cfg = cfg
                                    break

                            def classify_risk(val: float) -> str:
                                if not thresholds_cfg:
                                    return "unknown"
                                very_high = thresholds_cfg.get("very_high", thresholds_cfg.get("high", val + 1))
                                high = thresholds_cfg.get("high", thresholds_cfg.get("low", 0))
                                low = thresholds_cfg.get("low", thresholds_cfg.get("high", 0))
                                if val > very_high:
                                    return "very_high"
                                if val > high:
                                    return "high"
                                if val < low:
                                    return "low"
                                return "normal"

                            # Use the configured threshold as the base for consequence bands.
                            # Example: if threshold is 160, we treat 160–169, 170–179, and >=180 differently.
                            base_threshold = threshold_float
                            if base_threshold is None:
                                # Fallback to the metric's "high" threshold if no custom threshold was set
                                base_threshold = float(thresholds_cfg.get("high", 140.0)) if thresholds_cfg else 140.0

                            for p in all_patient_records:
                                if p["value"] is None:
                                    continue
                                val = float(p["value"])
                                risk_level = classify_risk(val)
                                p["risk_level"] = risk_level
                                above_threshold = threshold_float is not None and val >= threshold_float
                                p["above_threshold"] = above_threshold

                                consequences = None
                                if above_threshold:
                                    if val >= base_threshold + 20:
                                        # Very high above threshold (e.g. >= 180 when threshold is 160)
                                        consequences = (
                                            "Very high blood sugar far above the target range; "
                                            "there is increased risk of acute complications and long-term organ damage "
                                            "if this pattern persists. Urgent clinical review is recommended."
                                        )
                                    elif val >= base_threshold + 10:
                                        # Clearly above threshold (e.g. 170–179 when threshold is 160)
                                        consequences = (
                                            "Blood sugar is significantly above the agreed threshold; "
                                            "this increases the risk of diabetes-related complications and requires "
                                            "timely treatment adjustment and closer monitoring."
                                        )
                                    else:
                                        # Just above threshold (e.g. 160–169 when threshold is 160)
                                        consequences = (
                                            "Blood sugar is just above the threshold; "
                                            "early lifestyle and medication optimization can help prevent progression "
                                            "to more severe hyperglycemia."
                                        )

                                p["consequences"] = consequences

                            result["patient_records"] = all_patient_records
                            result["patients_above_threshold"] = [
                                p for p in all_patient_records if p["above_threshold"]
                            ]

                            # Cohort-level risk assessment for the metric
                            cohort_risk = risk_service.calculate_risk_score(
                                {metric_name: values}, privacy_budget=1.0
                            )
                            if cohort_risk.get("success"):
                                result["risk_score"] = cohort_risk["risk_score"]
                                result["risk_category"] = cohort_risk["risk_category"]
                                result["risk_factors"] = cohort_risk["risk_factors"]
                                result["risk_recommendations"] = cohort_risk["recommendations"]
                        except Exception as risk_exc:
                            result["risk_error"] = str(risk_exc)

        elif computation_type == "secure_variance":
            # For variance, we need to decrypt the values first
            decrypted_values = []
            for enc_val in all_encrypted_data:
                if self.homomorphic_encryption:
                    # Use service-level decrypt that reconstructs Paillier ciphertext from JSON-friendly dicts
                    decrypted_values.append(self.decrypt(enc_val))
                else:
                    # Handle fallback encryption
                    if isinstance(enc_val, dict) and enc_val.get('type') == 'fallback':
                        decrypted_values.append(Decimal(enc_val.get('encrypted', '0')))
                    else:
                        decrypted_values.append(enc_val)

            # Convert to float for statistics library
            float_values = [float(val) for val in decrypted_values]

            # Calculate variance
            try:
                result["variance"] = statistics.variance(float_values) if len(float_values) > 1 else 0
                result["std_dev"] = statistics.stdev(float_values) if len(float_values) > 1 else 0
            except Exception as e:
                result["variance_error"] = str(e)
                result["variance"] = 0
                result["std_dev"] = 0

        # Add security metadata
        result["security_method"] = "Homomorphic Encryption (Paillier)"

        return result
    
    def _perform_spec_based_computation(
        self,
        computation: SecureComputation,
        results: List[ComputationResult],
        spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform computation based on a generic ComputationSpec.
        
        This method extracts variables and operations from the spec,
        maps them to submitted data using VariableColumnMapping,
        and executes the appropriate secure computation.
        """
        from models import VariableColumnMapping
        
        try:
            # Extract variables and operations from spec
            variables = spec.get("variables", [])
            operations = spec.get("operations", [])
            analysis_type = spec.get("analysis_type", "basic_statistics")
            
            if not operations:
                raise ValueError("No operations specified in computation spec")
            
            # Get variable-to-column mappings for all participants
            org_data = {}  # org_id -> {variable_id: [values]}
            
            for result in results:
                org_id = result.org_id
                if org_id not in org_data:
                    org_data[org_id] = {}
                
                # Get confirmed mappings for this org
                mappings = self.db.query(VariableColumnMapping).filter(
                    VariableColumnMapping.computation_id == computation.computation_id,
                    VariableColumnMapping.org_id == org_id,
                    VariableColumnMapping.confirmed == True
                ).all()
                
                # Extract data points (could be dict with variable keys or flat list)
                data_points = result.data_points
                if isinstance(data_points, dict):
                    # Data is organized by variable/column
                    for mapping in mappings:
                        var_id = mapping.variable_id
                        col_name = mapping.column_name
                        if col_name in data_points:
                            if var_id not in org_data[org_id]:
                                org_data[org_id][var_id] = []
                            values = data_points[col_name]
                            if isinstance(values, list):
                                org_data[org_id][var_id].extend(values)
                            else:
                                org_data[org_id][var_id].append(values)
                else:
                    # Legacy: single column/list - use first variable
                    if variables and isinstance(data_points, list):
                        var_id = variables[0].get("id") or variables[0].get("name", "value")
                        if var_id not in org_data[org_id]:
                            org_data[org_id][var_id] = []
                        org_data[org_id][var_id].extend(data_points)
            
            # Execute operations based on spec
            computation_results = {}
            
            for op in operations:
                op_type = op.get("type", "").lower()
                op_id = op.get("id", "main_operation")
                
                # Determine which variables to use
                input_var = op.get("input")
                x_var = op.get("x")
                y_var = op.get("y")
                
                # Collect data for the operation
                if op_type in ["secure_mean", "secure_average", "secure_sum", "secure_variance"]:
                    # Single variable operation
                    var_id = input_var or (variables[0].get("id") if variables else "value")
                    all_values = []
                    for org_id, var_data in org_data.items():
                        if var_id in var_data:
                            all_values.extend(var_data[var_id])
                    
                    if op_type == "secure_mean" or op_type == "secure_average":
                        # Use existing secure computation
                        temp_result = self._perform_secure_computation_homomorphic("secure_average", results)
                        op_result = {
                            "type": "mean",
                            "value": temp_result.get("mean", 0),
                            "count": temp_result.get("count", 0)
                        }
                        
                        # Add threshold analysis if threshold is specified in options
                        op_options = op.get("options", {})
                        threshold_value = op_options.get("threshold")
                        
                        if threshold_value is not None:
                            try:
                                threshold_float = float(threshold_value)
                                from models import ComputationPatientRecord
                                
                                # Get all patient records for this computation
                                patient_records = self.db.query(ComputationPatientRecord).filter_by(
                                    computation_id=computation.computation_id
                                ).all()
                                
                                if patient_records:
                                    # Filter patients above threshold
                                    above_threshold_patients = []
                                    for record in patient_records:
                                        if record.value is not None:
                                            record_value = float(record.value)
                                            if record_value >= threshold_float:
                                                above_threshold_patients.append({
                                                    "patient_id": record.patient_id,
                                                    "value": record_value,
                                                    "org_id": record.org_id,
                                                    "metric_name": record.metric_name,
                                                    "above_threshold": True
                                                })
                                    
                                    op_result["threshold_value"] = threshold_float
                                    op_result["above_threshold_count"] = len(above_threshold_patients)
                                    op_result["above_threshold_percentage"] = (
                                        (len(above_threshold_patients) / len(patient_records)) * 100.0
                                    ) if patient_records else 0.0
                                    op_result["patients_above_threshold"] = above_threshold_patients
                                    
                                    # Add risk level classification
                                    try:
                                        from services.risk_stratification import RiskStratificationService
                                        risk_service = RiskStratificationService()
                                        
                                        # Find risk thresholds for this metric
                                        metric_name = var_id if var_id else "blood_sugar"
                                        thresholds_cfg = None
                                        for key, cfg in risk_service.risk_thresholds.items():
                                            if key in metric_name.lower():
                                                thresholds_cfg = cfg
                                                break
                                        
                                        def classify_risk(val: float) -> str:
                                            if not thresholds_cfg:
                                                return "unknown"
                                            very_high = thresholds_cfg.get("very_high", thresholds_cfg.get("high", val + 1))
                                            high = thresholds_cfg.get("high", thresholds_cfg.get("low", 0))
                                            low = thresholds_cfg.get("low", thresholds_cfg.get("high", 0))
                                            if val > very_high:
                                                return "very_high"
                                            if val > high:
                                                return "high"
                                            if val < low:
                                                return "low"
                                            return "normal"
                                        
                                        # Add risk levels to patients
                                        for patient in above_threshold_patients:
                                            patient["risk_level"] = classify_risk(patient["value"])
                                            
                                            # Add consequences based on how far above threshold
                                            val = patient["value"]
                                            if val >= threshold_float + 20:
                                                patient["consequences"] = (
                                                    "Very high blood sugar far above the target range; "
                                                    "there is increased risk of acute complications and long-term organ damage "
                                                    "if this pattern persists. Urgent clinical review is recommended."
                                                )
                                            elif val >= threshold_float + 10:
                                                patient["consequences"] = (
                                                    "Blood sugar is significantly above the agreed threshold; "
                                                    "this increases the risk of diabetes-related complications and requires "
                                                    "timely treatment adjustment and closer monitoring."
                                                )
                                            else:
                                                patient["consequences"] = (
                                                    "Blood sugar is just above the threshold; "
                                                    "early lifestyle and medication optimization can help prevent progression "
                                                    "to more severe hyperglycemia."
                                                )
                                    except Exception as risk_exc:
                                        logger.warning(f"Failed to add risk classification: {risk_exc}")
                                        # Continue without risk classification
                            
                            except (TypeError, ValueError) as e:
                                logger.warning(f"Invalid threshold value: {threshold_value}, error: {e}")
                        
                        computation_results[op_id] = op_result
                    elif op_type == "secure_sum":
                        temp_result = self._perform_secure_computation_homomorphic("secure_sum", results)
                        computation_results[op_id] = {
                            "type": "sum",
                            "value": temp_result.get("sum", 0),
                            "count": temp_result.get("count", 0)
                        }
                    elif op_type == "secure_variance":
                        temp_result = self._perform_secure_computation_homomorphic("secure_variance", results)
                        computation_results[op_id] = {
                            "type": "variance",
                            "value": temp_result.get("variance", 0),
                            "count": temp_result.get("count", 0)
                        }
                
                elif op_type == "secure_correlation":
                    # Two variable operation
                    if x_var and y_var:
                        # Use advanced SMPC correlation
                        computation_results[op_id] = self._perform_advanced_computation(
                            computation, results
                        )
                    else:
                        computation_results[op_id] = {"error": "Correlation requires x and y variables"}
                
                elif op_type in ["secure_regression", "cohort_analysis", "secure_survival", "categorical_filter", "anomaly_detection"]:
                    # Use advanced computation methods
                    # Handle anomaly detection
                    if op_type == "anomaly_detection":
                        # Collect all numeric values for anomaly detection
                        all_values = []
                        for org_id, var_data in org_data.items():
                            for var_id, values in var_data.items():
                                all_values.extend([float(v) for v in values if isinstance(v, (int, float))])
                        
                        if len(all_values) < 10:
                            computation_results[op_id] = {
                                "type": "anomaly_detection",
                                "error": "Insufficient data for anomaly detection (need at least 10 data points)",
                                "total_records": len(all_values),
                                "anomalies_detected": 0
                            }
                        else:
                            # Use advanced SMPC anomaly detection
                            # Prepare data in the format expected by advanced_smpc
                            all_shares = [[{"value": v} for v in all_values]]
                            computation_results[op_id] = self.advanced_smpc.secure_anomaly_detection(all_shares)
                            computation_results[op_id]["type"] = "anomaly_detection"
                    # For categorical_filter, extract filters from options
                    elif op_type == "categorical_filter" and op.get("options") and op["options"].get("filters"):
                        filters = op["options"]["filters"]
                        # Apply filters to patient records
                        from models import ComputationPatientRecord
                        patient_records = self.db.query(ComputationPatientRecord).filter_by(
                            computation_id=computation.computation_id
                        ).all()
                        
                        logger.info(f"Categorical filter: Found {len(patient_records)} patient records for computation {computation.computation_id}")
                        if len(patient_records) == 0:
                            error_msg = f"No patient records found for computation {computation.computation_id}. Data may not have been stored correctly during CSV upload. Please ensure CSV was uploaded with all columns."
                            logger.error(error_msg)
                            computation_results[op_id] = {
                                "type": "categorical_filter",
                                "filter_criteria": filters,
                                "matching_patients": [],
                                "count": 0,
                                "error": error_msg
                            }
                            continue
                        
                        # Group records by patient_id to check all their attributes
                        from collections import defaultdict
                        patient_data = defaultdict(dict)
                        for record in patient_records:
                            patient_id = record.patient_id
                            if record.metric_name:
                                # Handle categorical data stored as "COLUMN_NAME:VALUE"
                                if ":" in record.metric_name:
                                    col_name, col_value = record.metric_name.split(":", 1)
                                    patient_data[patient_id][col_name] = col_value
                                else:
                                    # Numeric data
                                    patient_data[patient_id][record.metric_name] = record.value
                            # Also store org_id for each patient
                            if "org_id" not in patient_data[patient_id]:
                                patient_data[patient_id]["org_id"] = record.org_id
                        
                        logger.info(f"Grouped patient data: {len(patient_data)} unique patients with attributes: {list(patient_data.values())[0].keys() if patient_data else 'none'}")
                        
                        # Log available columns for debugging
                        if patient_data:
                            sample_attrs = list(patient_data.values())[0]
                            logger.info(f"Sample patient attributes: {list(sample_attrs.keys())}")
                            logger.info(f"Filter keys to match: {list(filters.keys())}")
                        
                        filtered_patients = []
                        for patient_id, patient_attrs in patient_data.items():
                            match = True
                            
                            # Apply ALL filters dynamically - generic filter engine
                            for filter_key, filter_value in filters.items():
                                logger.debug(f"Applying filter: {filter_key} = {filter_value} for patient {patient_id}")
                                if not match:
                                    break  # Short-circuit if already failed
                                
                                # Use intelligent column matcher with learning capabilities
                                patient_value = None
                                
                                # Get available column names from patient attributes
                                available_columns = list(patient_attrs.keys())
                                
                                # Use intelligent matcher with database session for learning
                                try:
                                    from services.intelligent_column_matcher import IntelligentColumnMatcher
                                    # Pass database session so matcher can learn from past matches
                                    matcher = IntelligentColumnMatcher(db_session=self.db)
                                    match_result = matcher.find_best_match(filter_key, available_columns, min_confidence=0.4)
                                    
                                    if match_result:
                                        matched_column, confidence, reason = match_result
                                        patient_value = patient_attrs.get(matched_column)
                                        logger.info(f"Intelligent match: '{filter_key}' -> '{matched_column}' "
                                                   f"(confidence: {confidence:.2f}, reason: {reason})")
                                        
                                        # Learn from successful match (will be confirmed if computation succeeds)
                                        # The matcher already learns automatically, but we can boost confidence
                                        # if this match leads to successful results
                                    else:
                                        # Fallback: try exact case-insensitive match
                                        for attr_key, attr_val in patient_attrs.items():
                                            if attr_key.lower() == filter_key.lower():
                                                patient_value = patient_attrs.get(attr_key)
                                                logger.debug(f"Fallback exact match: '{filter_key}' -> '{attr_key}'")
                                                break
                                except Exception as match_err:
                                    logger.warning(f"Error in intelligent matching: {match_err}, using fallback")
                                    # Fallback to simple case-insensitive match
                                    for attr_key, attr_val in patient_attrs.items():
                                        if attr_key.lower() == filter_key.lower():
                                            patient_value = attr_val
                                            break
                                
                                # Log if we found the value or not
                                if patient_value is not None:
                                    logger.debug(f"Found value for {filter_key}: {patient_value} (type: {type(patient_value)})")
                                else:
                                    logger.warning(f"Could not find column matching filter key '{filter_key}' "
                                                 f"in patient attributes: {available_columns}")
                                
                                # Apply filter based on filter_value type
                                if isinstance(filter_value, dict):
                                    # Complex filter with operator
                                    if "operator" in filter_value:
                                        op = filter_value["operator"]
                                        filter_val = filter_value["value"]
                                        
                                        if patient_value is None:
                                            match = False
                                            continue
                                        
                                        # Convert patient_value for comparison
                                        try:
                                            # Handle "in" operator (check if value is in a list)
                                            if op == "in":
                                                # filter_val should be a list
                                                if isinstance(filter_val, list):
                                                    # Check if patient_value matches any value in the list (case-insensitive)
                                                    patient_val_str = str(patient_value).strip().upper()
                                                    filter_vals_upper = [str(v).strip().upper() for v in filter_val]
                                                    if patient_val_str not in filter_vals_upper:
                                                        match = False
                                                else:
                                                    # If filter_val is not a list, treat as single value
                                                    if str(patient_value).strip().upper() != str(filter_val).strip().upper():
                                                        match = False
                                            # Handle equality operator for strings
                                            elif op == "=" or op == "==":
                                                # Simple string equality (case-insensitive)
                                                if str(patient_value).strip().lower() != str(filter_val).strip().lower():
                                                    match = False
                                            elif (
                                                filter_key == "age"
                                                or "age" in filter_key.lower()
                                                or "blood_sugar" in filter_key.lower()
                                                or "glucose" in filter_key.lower()
                                            ):
                                                patient_num = float(patient_value)
                                                filter_num = float(filter_val)
                                                if op == "<" and patient_num >= filter_num:
                                                    match = False
                                                elif op == ">" and patient_num <= filter_num:
                                                    match = False
                                                elif op == "<=" and patient_num > filter_num:
                                                    match = False
                                                elif op == ">=" and patient_num < filter_num:
                                                    match = False
                                            elif "date" in filter_key.lower():
                                                # Date comparison (simplified - assumes ISO format)
                                                # Use datetime from module import
                                                from datetime import datetime as dt_module
                                                try:
                                                    patient_date = dt_module.fromisoformat(str(patient_value).split()[0])
                                                    filter_date = dt_module.fromisoformat(str(filter_val).split()[0])
                                                    if op == "<" and patient_date >= filter_date:
                                                        match = False
                                                    elif op == ">" and patient_date <= filter_date:
                                                        match = False
                                                    elif op == "<=" and patient_date > filter_date:
                                                        match = False
                                                    elif op == ">=" and patient_date < filter_date:
                                                        match = False
                                                except Exception:
                                                    # Fallback to string comparison
                                                    if op == "<=" and str(patient_value) > str(filter_val):
                                                        match = False
                                                    elif op == ">=" and str(patient_value) < str(filter_val):
                                                        match = False
                                        except (ValueError, TypeError):
                                            match = False
                                    
                                    elif "min" in filter_value or "max" in filter_value:
                                        # Range filter
                                        if patient_value is None:
                                            match = False
                                            continue
                                        try:
                                            patient_num = float(patient_value)
                                            if "min" in filter_value and patient_num < float(filter_value["min"]):
                                                match = False
                                            if "max" in filter_value and patient_num > float(filter_value["max"]):
                                                match = False
                                        except (ValueError, TypeError):
                                            match = False
                                
                                else:
                                    # Simple equality filter (string or exact match)
                                    if patient_value is None:
                                        match = False
                                        continue
                                    
                                    # Case-insensitive string comparison
                                    if str(patient_value).strip().lower() != str(filter_value).strip().lower():
                                        # Also try partial match for conditions
                                        if filter_key in ["condition", "diagnosis", "admission_reason"]:
                                            if str(filter_value).lower() not in str(patient_value).lower():
                                                match = False
                                        else:
                                            match = False
                            
                            if match:
                                # Include all patient attributes in the result
                                filtered_patients.append({
                                    "patient_id": patient_id,
                                    "org_id": patient_attrs.get("org_id"),
                                    **{k: v for k, v in patient_attrs.items() if k != "org_id"}  # Include all other attributes
                                })
                        
                        logger.info(f"Filter applied: {filters}, Found {len(filtered_patients)} matching patients out of {len(patient_data)} total patients")
                        if len(filtered_patients) == 0 and len(patient_data) > 0:
                            # Log sample patient data to help debug filter issues
                            sample_patient = list(patient_data.values())[0]
                            logger.warning(f"Filter returned 0 matches. Sample patient data: {sample_patient}")
                            logger.warning(f"Filter criteria: {filters}")
                        
                        # Learn from successful filter matches - store mappings for future use
                        if len(filtered_patients) > 0:
                            try:
                                from services.intelligent_column_matcher import IntelligentColumnMatcher
                                matcher = IntelligentColumnMatcher(db_session=self.db)
                                
                                # For each filter that successfully matched, learn the mapping
                                for filter_key in filters.keys():
                                    # Find which column was matched (from earlier in the loop)
                                    # We'll learn this when we actually use the match
                                    pass  # Learning happens during matching phase above
                            except Exception as learn_err:
                                logger.debug(f"Could not learn from filter matches: {learn_err}")
                        
                        computation_results[op_id] = {
                            "type": "categorical_filter",
                            "filter_criteria": filters,
                            "matching_patients": filtered_patients,
                            "count": len(filtered_patients)
                        }
                    else:
                        computation_results[op_id] = self._perform_advanced_computation(
                            computation, results
                        )
                
                else:
                    # Fallback: basic statistics
                    temp_result = self._perform_secure_computation_homomorphic("basic_statistics", results)
                    computation_results[op_id] = temp_result
            
            # Build final result
            final_result = {
                "spec_based": True,
                "analysis_type": analysis_type,
                "research_question": spec.get("research_question"),
                "operations": computation_results,
                "variables_used": [v.get("id") or v.get("name") for v in variables],
                "participants_count": len(org_data),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return final_result
        
        except Exception as e:
            logger.error(f"Error in spec-based computation: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": f"Spec-based computation failed: {str(e)}",
                "spec_based": True
            }
    
    def _perform_advanced_computation(self, computation: SecureComputation, results: List[ComputationResult]) -> Dict[str, Any]:
        """Perform advanced SMPC computations"""
        try:
            computation_type = computation.type.lower()
            parameters: Dict[str, Any] = computation.parameters or {}
            # Extract shares for advanced computation
            all_shares = []
            for result in results:
                if isinstance(result.data_points, dict) and "smpc_shares" in result.data_points:
                    shares = result.data_points["smpc_shares"]
                    if shares:
                        all_shares.extend(shares)
            
            if not all_shares:
                raise ValueError("No valid SMPC shares found for advanced computation")
            
            # Route to appropriate advanced computation
            computation_result = None
            if computation_type == "secure_correlation":
                computation_result = self.advanced_smpc.secure_correlation_analysis(all_shares)
            elif computation_type == "secure_regression":
                computation_result = self.advanced_smpc.secure_regression_analysis(all_shares)
            elif computation_type == "secure_survival":
                computation_result = self.advanced_smpc.secure_survival_analysis(all_shares)
            elif computation_type == "federated_logistic":
                computation_result = self.advanced_smpc.secure_federated_learning(all_shares, "logistic")
            elif computation_type == "federated_random_forest":
                computation_result = self.advanced_smpc.secure_federated_learning(all_shares, "random_forest")
            elif computation_type == "anomaly_detection":
                computation_result = self.advanced_smpc.secure_anomaly_detection(all_shares)
            elif computation_type == "cohort_analysis":
                # Use criteria from computation parameters if provided via generic spec
                criteria = parameters.get("criteria") or {"age_min": 18, "condition": "diabetes"}
                computation_result = self.advanced_smpc.secure_cohort_analysis(all_shares, criteria)
            elif computation_type == "drug_safety":
                computation_result = self.advanced_smpc.secure_drug_safety_analysis(all_shares)
            elif computation_type == "epidemiological":
                computation_result = self.advanced_smpc.secure_epidemiological_analysis(all_shares)
            elif computation_type == "secure_gwas":
                computation_result = self.advanced_smpc.secure_gwas_analysis(all_shares)
            elif computation_type == "pharmacogenomics":
                computation_result = self.advanced_smpc.secure_pharmacogenomics_analysis(all_shares)
            else:
                return {"error": f"Unknown advanced computation type: {computation_type}"}
            
            # Add security metadata to the result
            if computation_result and not computation_result.get("error"):
                computation_result["security_method"] = "Hybrid (Homomorphic Encryption + SMPC)"
                computation_result["count"] = len(all_shares)
            
            return computation_result
                
        except Exception as e:
            return {"error": f"Advanced computation failed: {str(e)}"}
    
    def _perform_secure_computation_homomorphic(self, computation_type: str, results: List[ComputationResult]) -> Dict[str, Any]:
        """Perform secure computation using homomorphic encryption"""
        # Extract encrypted values from results
        all_encrypted_data = []
        for result in results:
            print(f"DEBUG: Processing result.data_points: {type(result.data_points)} = {result.data_points}")
            # Handle both formats: direct list of encrypted values or dict with "homomorphic" key
            if isinstance(result.data_points, dict) and "homomorphic" in result.data_points:
                all_encrypted_data.extend(result.data_points["homomorphic"])
            elif isinstance(result.data_points, list):
                all_encrypted_data.extend(result.data_points)
        
        print(f"DEBUG: all_encrypted_data: {all_encrypted_data[:3]}...")  # Show first 3 items
        
        if not all_encrypted_data:
            raise ValueError("No valid encrypted data found in submissions")
        
        # Process based on computation type
        result = {}
        
        # Count is always available
        result["count"] = len(all_encrypted_data)
        
        if computation_type in ["basic_statistics", "health_statistics", "secure_average"]:
            # For basic statistics, we need to decrypt the values first
            decrypted_values = []
            for enc_val in all_encrypted_data:
                if self.homomorphic_encryption:
                    # Use service-level decrypt that reconstructs Paillier ciphertext from JSON-friendly dicts
                    decrypted_values.append(self.decrypt(enc_val))
                else:
                    # Handle fallback encryption
                    if isinstance(enc_val, dict) and enc_val.get('type') == 'fallback':
                        decrypted_values.append(Decimal(enc_val.get('encrypted', '0')))
                    else:
                        decrypted_values.append(enc_val)
            
            # Convert to float for statistics library
            float_values = [float(val) for val in decrypted_values]
            
            # Calculate basic statistics with error handling
            try:
                result["mean"] = statistics.mean(float_values)
                result["average"] = result["mean"]  # Add average alias
            except Exception as e:
                result["mean_error"] = str(e)
                
            try:
                result["sum"] = sum(float_values)
            except Exception as e:
                result["sum_error"] = str(e)
                
            try:
                result["std_dev"] = statistics.stdev(float_values) if len(float_values) > 1 else 0
            except Exception as e:
                result["std_dev_error"] = str(e)
                
            try:
                result["min"] = min(float_values)
                result["max"] = max(float_values)
                result["range"] = result["max"] - result["min"]
            except Exception as e:
                result["minmax_error"] = str(e)
                
            try:
                if len(float_values) >= 4:
                    quartiles = statistics.quantiles(float_values, n=4)
                    result["quartiles"] = [quartiles[0], quartiles[1], quartiles[2]]
                    result["iqr"] = quartiles[2] - quartiles[0]
            except Exception as e:
                result["quartiles_error"] = str(e)
                
            try:
                result["variance"] = statistics.variance(float_values) if len(float_values) > 1 else 0
            except Exception as e:
                result["variance_error"] = str(e)
                
            try:
                result["mode"] = statistics.mode(float_values) if len(float_values) > 1 else float_values[0]
            except Exception as e:
                result["mode_error"] = str(e)
        
        elif computation_type == "sum":
            # For sum, we can use homomorphic addition directly using the HE helper
            if self.homomorphic_encryption:
                try:
                    from homomorphic_encryption_enhanced import PaillierCiphertext
                    ciphertexts = []
                    for enc_val in all_encrypted_data:
                        if isinstance(enc_val, dict) and enc_val.get('type') == 'paillier':
                            ct_dict = enc_val['ciphertext'] if 'ciphertext' in enc_val else {k: enc_val[k] for k in ('value', 'public_key') if k in enc_val}
                            ciphertexts.append(PaillierCiphertext.from_dict(ct_dict))
                        else:
                            ciphertexts = None
                            break
                    if ciphertexts is not None and ciphertexts:
                        encrypted_sum = self.homomorphic_encryption.secure_sum(ciphertexts)
                        # Decrypt the final sum
                        result["sum"] = float(self.homomorphic_encryption.decrypt(encrypted_sum))
                    else:
                        # Fallback: decrypt and sum manually
                        decrypted_values = []
                        for enc_val in all_encrypted_data:
                            if isinstance(enc_val, dict) and enc_val.get('type') == 'fallback':
                                decrypted_values.append(float(enc_val.get('encrypted', '0')))
                            else:
                                decrypted_values.append(float(self.decrypt(enc_val)))
                        result["sum"] = sum(decrypted_values)
                except Exception:
                    # Fallback on error
                    decrypted_values = []
                    for enc_val in all_encrypted_data:
                        if isinstance(enc_val, dict) and enc_val.get('type') == 'fallback':
                            decrypted_values.append(float(enc_val.get('encrypted', '0')))
                        else:
                            decrypted_values.append(float(self.decrypt(enc_val)))
                    result["sum"] = sum(decrypted_values)
            else:
                # Fallback: decrypt and sum manually
                decrypted_values = []
                for enc_val in all_encrypted_data:
                    if isinstance(enc_val, dict) and enc_val.get('type') == 'fallback':
                        decrypted_values.append(float(enc_val.get('encrypted', '0')))
                    else:
                        decrypted_values.append(float(enc_val))
                result["sum"] = sum(decrypted_values)
            
        elif computation_type == "average":
            # For average, use homomorphic addition then divide
            if self.homomorphic_encryption:
                try:
                    from homomorphic_encryption_enhanced import PaillierCiphertext
                    ciphertexts = []
                    for enc_val in all_encrypted_data:
                        if isinstance(enc_val, dict) and enc_val.get('type') == 'paillier':
                            ct_dict = enc_val['ciphertext'] if 'ciphertext' in enc_val else {k: enc_val[k] for k in ('value', 'public_key') if k in enc_val}
                            ciphertexts.append(PaillierCiphertext.from_dict(ct_dict))
                        else:
                            ciphertexts = None
                            break
                    if ciphertexts is not None and ciphertexts:
                        # Debug: decrypt a small sample to verify scale
                        try:
                            sample_dec = []
                            for ct in ciphertexts[:5]:
                                sample_dec.append(float(self.homomorphic_encryption.decrypt(ct)))
                            print(f"[HOMOMORPHIC DEBUG] average: sample_dec_first5={sample_dec} count={len(ciphertexts)}")
                        except Exception as _e:
                            print(f"[HOMOMORPHIC DEBUG] average: sample decrypt failed: {_e}")
                        encrypted_sum = self.homomorphic_encryption.secure_sum(ciphertexts)
                        # Decrypt and divide by count
                        sum_value = self.homomorphic_encryption.decrypt(encrypted_sum)
                        try:
                            print(f"[HOMOMORPHIC DEBUG] average: dec_sum={float(sum_value)} divisor={len(all_encrypted_data)}")
                        except Exception:
                            pass
                        result["mean"] = float(sum_value) / len(all_encrypted_data)
                    else:
                        # Fallback: decrypt and calculate average manually
                        decrypted_values = []
                        for enc_val in all_encrypted_data:
                            if isinstance(enc_val, dict) and enc_val.get('type') == 'fallback':
                                decrypted_values.append(float(enc_val.get('encrypted', '0')))
                            else:
                                decrypted_values.append(float(self.decrypt(enc_val)))
                        result["mean"] = sum(decrypted_values) / len(decrypted_values) if decrypted_values else 0
                except Exception:
                    decrypted_values = []
                    for enc_val in all_encrypted_data:
                        if isinstance(enc_val, dict) and enc_val.get('type') == 'fallback':
                            decrypted_values.append(float(enc_val.get('encrypted', '0')))
                        else:
                            decrypted_values.append(float(self.decrypt(enc_val)))
                    result["mean"] = sum(decrypted_values) / len(decrypted_values) if decrypted_values else 0
            else:
                # Fallback: decrypt and calculate average manually
                decrypted_values = []
                for enc_val in all_encrypted_data:
                    if isinstance(enc_val, dict) and enc_val.get('type') == 'fallback':
                        decrypted_values.append(float(enc_val.get('encrypted', '0')))
                    else:
                        decrypted_values.append(float(enc_val))
                result["mean"] = sum(decrypted_values) / len(decrypted_values) if decrypted_values else 0
        
        # Add security metadata
        result["security_method"] = "Homomorphic Encryption (Paillier)"
        
        return result

    async def check_expiring_requests(self):
        """Check for computation requests that will expire soon and notify organizations"""
        try:
            # Define expiration thresholds
            expiration_date = datetime.utcnow() - timedelta(days=7)  # Requests expire after 7 days
            warning_date = datetime.utcnow() - timedelta(days=6)     # Warn when 1 day left before expiration
            
            # Find computations that will expire soon
            expiring_soon = self.db.query(SecureComputation).filter(
                SecureComputation.status.in_(["initialized", "waiting_for_participants"]),
                SecureComputation.created_at <= warning_date,
                SecureComputation.created_at > expiration_date
            ).all()
            
            # For each expiring computation, find organizations that haven't responded
            for comp in expiring_soon:
                # Get all organizations that haven't joined yet
                from models import Organization
                all_orgs = self.db.query(Organization).all()
                participant_orgs = self.db.query(ComputationParticipant.org_id).filter_by(
                    computation_id=comp.computation_id
                ).all()
                participant_org_ids = [p.org_id for p in participant_orgs]
                
                # Get creator org info
                creator_org = self.db.query(Organization).filter_by(id=comp.org_id).first()
                
                # Calculate days until expiration
                days_until_expiration = 7 - (datetime.utcnow() - comp.created_at).days
                
                # Prepare notification data
                notification_data = {
                    "computation_id": comp.computation_id,
                    "title": f"{comp.type.replace('_', ' ').title()} Computation",
                    "description": f"Secure computation request for {comp.type}",
                    "computation_type": comp.type,
                    "security_method": "SMPC + Homomorphic Encryption",
                    "requester_org": creator_org.name if creator_org else "Unknown Organization",
                    "created_at": comp.created_at.isoformat() if comp.created_at else None,
                    "status": "pending",
                    "expires_in_days": days_until_expiration
                }
                
                # Notify each organization that hasn't responded yet
                for org in all_orgs:
                    # Skip creator and existing participants
                    if org.id == comp.org_id or org.id in participant_org_ids:
                        continue
                    
                    # Notify organization about expiring request
                    from websocket import smpc_manager
                    await smpc_manager.notify_request_expiring_soon(org.id, notification_data)
            
            return True
        except Exception as e:
            print(f"Error checking expiring requests: {e}")
            return False
    
    def list_computations(self, org_id):
        """List all computations for an organization with proper status tracking"""
        try:
            # Get computations where org is creator or participant
            creator_computations = self.db.query(SecureComputation).filter(
                SecureComputation.org_id == org_id
            ).all()
            
            participant_computations = self.db.query(SecureComputation).join(
                ComputationParticipant,
                SecureComputation.computation_id == ComputationParticipant.computation_id
            ).filter(
                ComputationParticipant.org_id == org_id
            ).all()
            
            # Combine and deduplicate
            all_computations = {comp.computation_id: comp for comp in creator_computations}
            for comp in participant_computations:
                all_computations[comp.computation_id] = comp
            
            result = []
            for comp in all_computations.values():
                # Get participant and submission counts
                participants_count = self.db.query(ComputationParticipant).filter_by(
                    computation_id=comp.computation_id
                ).count()
                submissions_count = self.db.query(ComputationResult).filter_by(
                    computation_id=comp.computation_id
                ).count()
                
                # Determine proper status
                status = comp.status
                if status == "initialized" and participants_count > 1:
                    status = "waiting_for_data"
                elif status == "initialized" and participants_count <= 1:
                    status = "waiting_for_participants"
                elif submissions_count > 0 and submissions_count < participants_count:
                    status = "waiting_for_data"
                elif submissions_count >= participants_count and submissions_count >= 3:
                    if status not in ["completed", "error"]:
                        status = "ready_to_compute"
                
                result.append({
                    "computation_id": comp.computation_id,
                    "org_id": comp.org_id,  # Include the creator org_id
                    "type": comp.type,
                    "status": status,
                    "result": comp.result,
                    "created_at": comp.created_at.isoformat() if comp.created_at else None,
                    "completed_at": comp.completed_at.isoformat() if comp.completed_at else None,
                    "participants_count": participants_count,
                    "submissions_count": submissions_count,
                    "error_message": comp.error_message
                })
            
            return result
        except Exception as e:
            print(f"Error listing computations: {e}")
            return []

class SecureHealthMetricsComputation:
    def __init__(self):
        self.computations = {}

    def initialize_computation(self, computation_id: str, metric_type: str, participating_orgs: List[str], security_method: str = "standard", threshold: int = 2, min_participants: int = 3) -> bool:
        self.computations[computation_id] = {
            "metric_type": metric_type,
            "organizations": set(participating_orgs),
            "shares_submitted": set(),
            "values": {},
            "status": "initialized",
            "start_time": datetime.utcnow().isoformat(),
            "security_method": security_method,
            "threshold": threshold,
            "min_participants": min_participants
        }
        return True

    def submit_metric(self, computation_id: str, org_id: str, value: float) -> Dict[str, Any]:
        if computation_id not in self.computations:
            return {
                "success": False,
                "error": "Computation not found",
                "error_code": "COMPUTATION_NOT_FOUND"
            }
            
        comp = self.computations[computation_id]
        
        # Check if computation is already completed or in error state
        if comp["status"] == "completed":
            return {
                "success": False,
                "error": "Computation already completed",
                "error_code": "ALREADY_COMPLETED"
            }
            
        if comp["status"] == "error":
            return {
                "success": False,
                "error": comp.get("error", "Computation is in error state"),
                "error_code": comp.get("error_code", "COMPUTATION_ERROR")
            }
        
        # Check if organization is allowed to participate
        if org_id not in comp["organizations"]:
            return {
                "success": False,
                "error": "Organization not authorized to participate in this computation",
                "error_code": "UNAUTHORIZED_ORGANIZATION"
            }
            
        # Check if organization already submitted data
        if org_id in comp["shares_submitted"]:
            return {
                "success": False,
                "error": "Organization already submitted data for this computation",
                "error_code": "DUPLICATE_SUBMISSION"
            }
            
        try:
            # Ensure value is numeric
            if not isinstance(value, (int, float)):
                return {
                    "success": False,
                    "error": "Non-numeric value in submission",
                    "error_code": "INVALID_DATA_TYPE"
                }
                
            # Store the value
            comp["values"][org_id] = value
            comp["shares_submitted"].add(org_id)
            
            # Update submission timestamp
            if "submission_timestamps" not in comp:
                comp["submission_timestamps"] = {}
            comp["submission_timestamps"][org_id] = datetime.utcnow().isoformat()
            
            return {
                "success": True,
                "message": "Data successfully submitted",
                "submission_time": comp["submission_timestamps"][org_id],
                "submissions_count": len(comp["shares_submitted"]),
                "total_organizations": len(comp["organizations"])
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error processing submission: {str(e)}",
                "error_code": "SUBMISSION_PROCESSING_ERROR"
            }

    def compute_aggregate_metrics(self, computation_id: str) -> Dict[str, Any]:
        try:
            if computation_id not in self.computations:
                raise ValueError("Computation not found")
            
            comp = self.computations[computation_id]
            
            # Check if computation is already in error state
            if comp["status"] == "error":
                return {
                    "status": "error",
                    "error": comp.get("error", "Unknown error occurred"),
                    "error_code": comp.get("error_code", "UNKNOWN_ERROR"),
                    "timestamp": comp.get("end_time", datetime.utcnow().isoformat())
                }
            
            # Check if computation is already completed
            if comp["status"] == "completed" and "result" in comp:
                return comp["result"]
            
            # Update status to processing
            comp["status"] = "processing"
            
            # Check if minimum participants requirement is met
            min_participants = comp.get("min_participants", 3)
            threshold = comp.get("threshold", 2)
            security_method = comp.get("security_method", "standard")
            
            # For hybrid security method, we need at least threshold participants
            if security_method == "hybrid" and len(comp["shares_submitted"]) < threshold:
                comp["status"] = "waiting_for_threshold"
                missing_orgs = list(comp["organizations"] - comp["shares_submitted"])
                return {
                    "status": "waiting_for_threshold",
                    "submitted": len(comp["shares_submitted"]),
                    "total": len(comp["organizations"]),
                    "threshold": threshold,
                    "missing": missing_orgs,
                    "progress_percentage": int((len(comp["shares_submitted"]) / threshold) * 100),
                    "message": f"Waiting for threshold of {threshold} participants. Currently have {len(comp['shares_submitted'])}."
                }
            
            # For all methods, check if minimum participants requirement is met
            if len(comp["shares_submitted"]) < min_participants:
                comp["status"] = "waiting_for_data"
                missing_orgs = list(comp["organizations"] - comp["shares_submitted"])
                return {
                    "status": "waiting_for_data",
                    "submitted": len(comp["shares_submitted"]),
                    "total": len(comp["organizations"]),
                    "min_participants": min_participants,
                    "missing": missing_orgs,
                    "progress_percentage": int((len(comp["shares_submitted"]) / min_participants) * 100),
                    "message": f"Waiting for minimum of {min_participants} participants. Currently have {len(comp['shares_submitted'])}."
                }
            
            values = list(comp["values"].values())
            
            # Basic statistics
            result = {
                "mean": statistics.mean(values),
                "median": statistics.median(values),
                "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "range": max(values) - min(values) if values else 0
            }
            
            # Advanced statistics if we have enough data points
            if len(values) >= 4:
                quartiles = statistics.quantiles(values, n=4)
                result["quartiles"] = {
                    "q1": quartiles[0],
                    "q2": quartiles[1],  # Same as median
                    "q3": quartiles[2]
                }
                result["interquartile_range"] = quartiles[2] - quartiles[0]
            
            # Calculate variance
            if len(values) > 1:
                result["variance"] = statistics.variance(values)
            
            # Calculate mode if applicable
            try:
                result["mode"] = statistics.mode(values)
            except statistics.StatisticsError:
                # No unique mode
                result["mode"] = None
            
            comp["status"] = "completed"
            comp["end_time"] = datetime.utcnow().isoformat()
            comp["result"] = result
            
            return result
        except Exception as e:
            # Handle errors
            if computation_id in self.computations:
                self.computations[computation_id]["status"] = "error"
                self.computations[computation_id]["error"] = str(e)
                self.computations[computation_id]["end_time"] = datetime.utcnow().isoformat()
            
            raise ValueError(f"Computation failed: {str(e)}")

    def get_computation_status(self, computation_id: str) -> Dict[str, Any]:
        if computation_id not in self.computations:
            raise ValueError("Computation not found")
        
        comp = self.computations[computation_id]
        security_method = comp.get("security_method", "standard")
        threshold = comp.get("threshold", 2)
        min_participants = comp.get("min_participants", 3)
        
        # Calculate progress percentage based on security method
        if security_method == "hybrid":
            # For hybrid, progress is based on reaching threshold
            progress_percentage = int((len(comp["shares_submitted"]) / threshold) * 100) if threshold > 0 else 0
            if progress_percentage > 100:
                progress_percentage = 100
        else:
            # For other methods, progress is based on reaching min_participants
            progress_percentage = int((len(comp["shares_submitted"]) / min_participants) * 100) if min_participants > 0 else 0
            if progress_percentage > 100:
                progress_percentage = 100
        
        status_info = {
            "status": comp["status"],
            "metric_type": comp["metric_type"],
            "security_method": security_method,
            "threshold": threshold if security_method == "hybrid" else None,
            "min_participants": min_participants,
            "participants_total": len(comp["organizations"]),
            "participants_submitted": len(comp["shares_submitted"]),
            "participants_pending": len(comp["organizations"]) - len(comp["shares_submitted"]),
            "start_time": comp["start_time"],
            "end_time": comp.get("end_time"),
            "result": comp.get("result"),
            "progress_percentage": progress_percentage
        }
        
        # Add error information if available
        if comp["status"] == "error" and "error" in comp:
            status_info["error"] = comp["error"]
        
        # Add missing participants if not all have submitted
        if len(comp["shares_submitted"]) < len(comp["organizations"]):
            status_info["missing_participants"] = list(comp["organizations"] - comp["shares_submitted"])
        
        return status_info

# Example usage of secure computation
def example_secure_analysis():
    """
    Example of how to use the secure computation service.
    This is just for demonstration purposes.
    """
    # Initialize service
    service = SecureComputationService(db_session)
    
    # Start a new computation with standard encryption
    standard_computation_id = service.create_computation(org_id=1, computation_type="health_statistics")
    
    # Add participants
    service.join_computation(standard_computation_id, org_id=1)
    service.join_computation(standard_computation_id, org_id=2)
    service.join_computation(standard_computation_id, org_id=3)
    
    # Submit data from each participant
    service.submit_data(standard_computation_id, org_id=1, data_points=[120, 118, 122])
    service.submit_data(standard_computation_id, org_id=2, data_points=[115, 125, 130])
    service.submit_data(standard_computation_id, org_id=3, data_points=[110, 112, 118])
    
    # Perform standard computation
    success = service.perform_computation(standard_computation_id)
    
    if success:
        # Get the results
        result = service.get_computation_result(standard_computation_id)
        print(f"Standard computation completed: {result}")
    else:
        print("Standard computation failed")
    
    # Create a new computation with homomorphic encryption
    homomorphic_computation_id = service.create_computation(org_id=1, computation_type="sum")
    
    # Add participants
    service.join_computation(homomorphic_computation_id, org_id=1)
    service.join_computation(homomorphic_computation_id, org_id=2)
    service.join_computation(homomorphic_computation_id, org_id=3)
    
    # Submit data from each participant (homomorphic encryption)
    service.submit_data(homomorphic_computation_id, org_id=1, data_points=[45, 50, 55])
    service.submit_data(homomorphic_computation_id, org_id=2, data_points=[40, 45, 50])
    service.submit_data(homomorphic_computation_id, org_id=3, data_points=[50, 55, 60])
    
    # Perform the computation
    success = service.perform_computation(homomorphic_computation_id)
    
    if success:
        # Get the results
        result = service.get_computation_result(homomorphic_computation_id)
        print(f"Homomorphic computation completed: {result}")
    else:
        print("Homomorphic computation failed")
    
    # Create a new computation with hybrid approach (SMPC + homomorphic)
    hybrid_computation_id = service.create_computation(org_id=1, computation_type="secure_mean")
    
    # Add participants
    service.join_computation(hybrid_computation_id, org_id=1)
    service.join_computation(hybrid_computation_id, org_id=2)
    service.join_computation(hybrid_computation_id, org_id=3)
    
    # Submit data from each participant (hybrid encryption)
    service.submit_data(hybrid_computation_id, org_id=1, data_points=[45, 50, 55])
    service.submit_data(hybrid_computation_id, org_id=2, data_points=[40, 45, 50])
    service.submit_data(hybrid_computation_id, org_id=3, data_points=[50, 55, 60])
    
    # Perform the computation
    success = service.perform_computation(hybrid_computation_id)
    
    if success:
        # Get the results
        result = service.get_computation_result(hybrid_computation_id)
        print(f"Hybrid computation completed: {result}")
    else:
        print("Hybrid computation failed")
    
    return "Example completed successfully"