from models import SessionLocal, SecureComputation, ComputationParticipant, ComputationInvitation, ComputationResult, SecureComputationResult


def main() -> None:
    db = SessionLocal()
    try:
        total_computations = db.query(SecureComputation).count()
        if total_computations == 0:
            print("No secure computations found. Nothing to delete.")
            return

        print("=== Secure Computations Cleanup ===")
        print(f"Found {total_computations} computations.")

        confirm = input(
            "This will permanently delete ALL computations and related data. "
            "Type 'DELETE' to confirm: "
        ).strip()
        if confirm != "DELETE":
            print("Aborted. No data was deleted.")
            return

        computation_ids = [
            c[0] for c in db.query(SecureComputation.computation_id).all()
        ]

        if not computation_ids:
            print("No computation IDs found. Nothing to delete.")
            return

        deleted_results = db.query(ComputationResult).filter(
            ComputationResult.computation_id.in_(computation_ids)
        ).delete(synchronize_session=False)

        deleted_participants = db.query(ComputationParticipant).filter(
            ComputationParticipant.computation_id.in_(computation_ids)
        ).delete(synchronize_session=False)

        deleted_invitations = db.query(ComputationInvitation).filter(
            ComputationInvitation.computation_id.in_(computation_ids)
        ).delete(synchronize_session=False)

        deleted_secure_results = db.query(SecureComputationResult).filter(
            SecureComputationResult.computation_id.in_(computation_ids)
        ).delete(synchronize_session=False)

        deleted_computations = db.query(SecureComputation).delete(
            synchronize_session=False
        )

        db.commit()

        print("Cleanup complete:")
        print(f"  Secure computations deleted: {deleted_computations}")
        print(f"  Computation results deleted: {deleted_results}")
        print(f"  Computation participants deleted: {deleted_participants}")
        print(f"  Computation invitations deleted: {deleted_invitations}")
        print(f"  Secure computation results deleted: {deleted_secure_results}")

    except Exception as exc:
        db.rollback()
        print(f"Error during cleanup: {exc}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
