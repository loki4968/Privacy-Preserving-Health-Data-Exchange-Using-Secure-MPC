import asyncio
from models import SessionLocal, Organization, ComputationParticipant, OrgType
from secure_computation import SecureComputationService

# Computation types to test
COMPUTATION_TYPES = [
    'health_statistics',
    'secure_sum',
    'secure_mean',
    'secure_variance',
    'secure_std_dev',
    'secure_correlation',
    'linear_regression',
    'logistic_regression',
]

async def run_test():
    db = SessionLocal()
    service = SecureComputationService(db)

    # Create dummy organizations
    org1 = db.query(Organization).filter_by(name="Test Org 1").first()
    if not org1:
        org1 = Organization(
            name="Test Org 1",
            email="testorg1@example.com",
            contact="0000000001",
            type=OrgType.HOSPITAL,
            location="Test City",
            privacy_accepted=True,
            password_hash="test",
        )
        db.add(org1)
    
    org2 = db.query(Organization).filter_by(name="Test Org 2").first()
    if not org2:
        org2 = Organization(
            name="Test Org 2",
            email="testorg2@example.com",
            contact="0000000002",
            type=OrgType.CLINIC,
            location="Test City",
            privacy_accepted=True,
            password_hash="test",
        )
        db.add(org2)
    
    db.commit()

    print("--- Starting Computation Verification ---")
    
    for comp_type in COMPUTATION_TYPES:
        print(f"\n--- Testing: {comp_type} ---")
        computation_id = service.create_computation(org_id=org1.id, computation_type=comp_type)
        
        # Add participants
        db.add(ComputationParticipant(computation_id=computation_id, org_id=org1.id))
        db.add(ComputationParticipant(computation_id=computation_id, org_id=org2.id))
        db.commit()

        # Submit data
        if comp_type == 'secure_correlation' or comp_type == 'linear_regression':
            await service.submit_data(computation_id, org1.id, [{'x': 1, 'y': 2}, {'x': 2, 'y': 3}])
            await service.submit_data(computation_id, org2.id, [{'x': 3, 'y': 4}, {'x': 4, 'y': 5}])
        elif comp_type == 'logistic_regression':
            await service.submit_data(computation_id, org1.id, [{'features': [1, 2], 'label': 0}, {'features': [2, 3], 'label': 0}])
            await service.submit_data(computation_id, org2.id, [{'features': [3, 4], 'label': 1}, {'features': [4, 5], 'label': 1}])
        else:
            await service.submit_data(computation_id, org1.id, [1, 2, 3])
            await service.submit_data(computation_id, org2.id, [4, 5, 6])

        # Perform computation
        success = await service.perform_computation(computation_id)
        if not success:
            print(f"[FAIL] {comp_type}: Computation failed to perform.")
            continue

        # Verify result
        computation = service.get_computation(computation_id)
        if computation and computation.result:
            print(f"[SUCCESS] {comp_type}: Computation successful.")
            # print(f"Result: {computation.result}")
        else:
            print(f"[FAIL] {comp_type}: Computation did not produce a result.")

    print("\n--- Verification Complete ---")
    db.close()

if __name__ == "__main__":
    asyncio.run(run_test())
