#!/usr/bin/env python3
"""
Cleanup script to remove previously computed computations from the database.
This script removes computation data and associated files but preserves user accounts and other important data.
"""

import sqlite3
import os
from datetime import datetime, timedelta
import shutil

DB_PATHS = [
    'health_data.db',
    'health.db',
    # Include backend DB copies if present
    os.path.join('backend', 'health_data.db'),
    os.path.join('backend', 'health.db'),
]

def cleanup_old_files(db_path):
    """Remove old uploaded files that are no longer referenced in the database.

    This scans both top-level `uploads/` and `backend/uploads/` so we catch all org folders.
    """

    print(f"🗂️ Starting File Cleanup for database: {db_path}")
    print("=" * 50)

    upload_dirs = [
        os.path.join('uploads'),
        os.path.join('backend', 'uploads'),
    ]

    # Filter to only existing directories
    upload_dirs = [d for d in upload_dirs if os.path.exists(d)]
    if not upload_dirs:
        print("📁 No uploads directories found (looked for 'uploads/' and 'backend/uploads/')")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Get all file references that are still in DB, including org_id to build paths
        cursor.execute("SELECT filename, org_id FROM uploads WHERE status != 'error'")
        referenced_files = set()
        for filename, org_id in cursor.fetchall():
            if not filename or org_id is None:
                continue
            for base_dir in upload_dirs:
                full_path = os.path.join(base_dir, str(org_id), filename)
                referenced_files.add(os.path.normpath(full_path))

        # Also get report files that are referenced
        try:
            cursor.execute("SELECT report_file_path FROM report_requests WHERE report_file_path IS NOT NULL")
            for (report_path,) in cursor.fetchall():
                if report_path:
                    referenced_files.add(os.path.normpath(report_path))
        except sqlite3.OperationalError:
            # Table may not exist in some DBs
            pass

        print(f"Found {len(referenced_files)} files still referenced in database")

        # Walk through all upload directories and find files to remove
        files_to_remove = []
        total_size_to_remove = 0

        for uploads_dir in upload_dirs:
            for root, dirs, files in os.walk(uploads_dir):
                for file in files:
                    file_path = os.path.normpath(os.path.join(root, file))
                    if file_path not in referenced_files:
                        files_to_remove.append(file_path)
                        try:
                            total_size_to_remove += os.path.getsize(file_path)
                        except OSError:
                            pass

        print(f"Found {len(files_to_remove)} unreferenced files to remove")
        print(f"  Total size to remove: {total_size_to_remove / 1024 / 1024:.2f} MB")

        # Remove the files
        removed_count = 0
        for file_path in files_to_remove:
            try:
                os.remove(file_path)
                removed_count += 1
                # Remove empty directories upward
                dir_path = os.path.dirname(file_path)
                # Try removing empty parent org dir, then its parent if empty
                for _ in range(3):
                    if os.path.exists(dir_path) and not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        dir_path = os.path.dirname(dir_path)
                    else:
                        break
            except Exception as e:
                print(f"Error removing {file_path}: {str(e)}")

        print(f"✅ Removed {removed_count} unreferenced files")

    except Exception as e:
        print(f"❌ Error during file cleanup: {str(e)}")
    finally:
        conn.close()

def cleanup_old_computations(db_path):
    """Remove old/completed computations and associated data."""

    print(f"\n🧹 Starting Computation Cleanup for database: {db_path}")
    print("=" * 50)

    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Disable foreign key constraints temporarily to allow deletion
    # We'll manually ensure referential integrity by deleting child tables first
    cursor.execute("PRAGMA foreign_keys = OFF")
    # Verify it's disabled
    cursor.execute("PRAGMA foreign_keys")
    fk_status = cursor.fetchone()[0]
    if fk_status != 0:
        print(f"⚠️  Warning: Foreign keys are still enabled (status: {fk_status})")

    try:
        # Create backup before cleanup
        backup_name = f"{db_path}_backup_before_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        print(f"📦 Creating backup: {backup_name}")
        shutil.copy2(db_path, backup_name)

        # Get initial counts
        print("\n📊 Initial Database State:")

        cursor.execute("SELECT COUNT(*) FROM secure_computations")
        initial_computations = cursor.fetchone()[0]
        print(f"  Secure computations: {initial_computations}")

        cursor.execute("SELECT COUNT(*) FROM computation_results")
        initial_results = cursor.fetchone()[0]
        print(f"  Computation results: {initial_results}")

        cursor.execute("SELECT COUNT(*) FROM secure_computation_results")
        initial_secure_results = cursor.fetchone()[0]
        print(f"  Secure computation results: {initial_secure_results}")

        cursor.execute("SELECT COUNT(*) FROM computation_participants")
        initial_participants = cursor.fetchone()[0]
        print(f"  Computation participants: {initial_participants}")

        # Try to get counts for optional tables
        try:
            cursor.execute("SELECT COUNT(*) FROM computation_patient_records")
            initial_patient_records = cursor.fetchone()[0]
            print(f"  Computation patient records: {initial_patient_records}")
        except sqlite3.OperationalError:
            initial_patient_records = 0
            print(f"  Computation patient records: (table not found)")

        try:
            cursor.execute("SELECT COUNT(*) FROM variable_column_mappings")
            initial_mappings = cursor.fetchone()[0]
            print(f"  Variable column mappings: {initial_mappings}")
        except sqlite3.OperationalError:
            initial_mappings = 0
            print(f"  Variable column mappings: (table not found)")

        # Find computations to remove (completed or old ones)
        # Remove computations that are:
        # 1. Status is 'completed' or 'error'
        # 2. Older than 30 days
        # 3. Status is 'failed' or 'cancelled'

        thirty_days_ago = datetime.now() - timedelta(days=30)
        thirty_days_ago_str = thirty_days_ago.strftime('%Y-%m-%d %H:%M:%S')

        print(f"\n🔍 Finding computations to remove (completed/error/failed/cancelled or older than {thirty_days_ago.date()})")

        # Get computation IDs to remove
        cursor.execute("""
            SELECT id, computation_id, status, created_at
            FROM secure_computations
            WHERE status IN ('completed', 'error', 'failed', 'cancelled')
               OR created_at < ?
        """, (thirty_days_ago_str,))

        computations_to_remove = cursor.fetchall()
        computation_ids_to_remove = [comp[1] for comp in computations_to_remove]  # computation_id strings
        secure_comp_ids_to_remove = [comp[0] for comp in computations_to_remove]  # id integers

        print(f"Found {len(computations_to_remove)} computations to remove:")
        for comp in computations_to_remove[:5]:  # Show first 5
            print(f"  ID: {comp[0]}, Status: {comp[2]}, Created: {comp[3]}")
        if len(computations_to_remove) > 5:
            print(f"  ... and {len(computations_to_remove) - 5} more")

        if not computations_to_remove:
            print("✅ No computations found to remove")
            conn.close()
            return

        # Remove computation results first (foreign key constraints)
        # Order matters: delete child tables before parent tables
        print("\n🗑️ Removing computation-related data...")
        if computation_ids_to_remove:
            placeholders = ','.join('?' * len(computation_ids_to_remove))
            
            # 1. Remove computation_patient_records (stores individual patient data)
            try:
                cursor.execute(f"""
                    DELETE FROM computation_patient_records
                    WHERE computation_id IN ({placeholders})
                """, computation_ids_to_remove)
                deleted_patient_records = cursor.rowcount
                print(f"  Removed {deleted_patient_records} patient records")
            except sqlite3.OperationalError as e:
                print(f"  Note: computation_patient_records table may not exist: {e}")
            
            # 2. Remove variable_column_mappings (stores column mappings)
            try:
                cursor.execute(f"""
                    DELETE FROM variable_column_mappings
                    WHERE computation_id IN ({placeholders})
                """, computation_ids_to_remove)
                deleted_mappings = cursor.rowcount
                print(f"  Removed {deleted_mappings} variable column mappings")
            except sqlite3.OperationalError as e:
                print(f"  Note: variable_column_mappings table may not exist: {e}")
            
            # 3. Remove from computation_results
            try:
                cursor.execute(f"""
                    DELETE FROM computation_results
                    WHERE computation_id IN ({placeholders})
                """, computation_ids_to_remove)
                deleted_results = cursor.rowcount
                print(f"  Removed {deleted_results} computation results")
            except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
                print(f"  Error removing computation_results: {e}")
                deleted_results = 0

            # 4. Remove from secure_computation_results
            try:
                cursor.execute(f"""
                    DELETE FROM secure_computation_results
                    WHERE computation_id IN ({placeholders})
                """, computation_ids_to_remove)
                deleted_secure_results = cursor.rowcount
                print(f"  Removed {deleted_secure_results} secure computation results")
            except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
                print(f"  Error removing secure_computation_results: {e}")
                deleted_secure_results = 0

            # 5. Remove computation participants
            try:
                cursor.execute(f"""
                    DELETE FROM computation_participants
                    WHERE computation_id IN ({placeholders})
                """, computation_ids_to_remove)
                deleted_participants = cursor.rowcount
                print(f"  Removed {deleted_participants} computation participants")
            except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
                print(f"  Error removing computation_participants: {e}")
                deleted_participants = 0

        # 6. Remove computation invitations (note: invitations.computation_id references the STRING computation_id)
        if computation_ids_to_remove:
            placeholders = ','.join('?' * len(computation_ids_to_remove))
            try:
                cursor.execute(f"""
                    DELETE FROM computation_invitations
                    WHERE computation_id IN ({placeholders})
                """, computation_ids_to_remove)
                deleted_invitations = cursor.rowcount
                print(f"  Removed {deleted_invitations} computation invitations")
            except sqlite3.OperationalError as e:
                print(f"  Note: computation_invitations table may not exist: {e}")

        # Finally remove the secure computations themselves
        # Use computation_id (string UUID) instead of id, since all foreign keys reference computation_id
        if computation_ids_to_remove:
            placeholders = ','.join('?' * len(computation_ids_to_remove))
            
            # Debug: Check for any remaining references before deletion
            print("\n🔍 Checking for remaining references...")
            try:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM computation_patient_records
                    WHERE computation_id IN ({placeholders})
                """, computation_ids_to_remove)
                remaining_patient_records = cursor.fetchone()[0]
                if remaining_patient_records > 0:
                    print(f"  ⚠️  Warning: {remaining_patient_records} patient records still exist")
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM variable_column_mappings
                    WHERE computation_id IN ({placeholders})
                """, computation_ids_to_remove)
                remaining_mappings = cursor.fetchone()[0]
                if remaining_mappings > 0:
                    print(f"  ⚠️  Warning: {remaining_mappings} variable mappings still exist")
            except sqlite3.OperationalError:
                pass
            
            cursor.execute(f"""
                SELECT COUNT(*) FROM computation_results
                WHERE computation_id IN ({placeholders})
            """, computation_ids_to_remove)
            remaining_results = cursor.fetchone()[0]
            if remaining_results > 0:
                print(f"  ⚠️  Warning: {remaining_results} computation results still exist")
            
            cursor.execute(f"""
                SELECT COUNT(*) FROM secure_computation_results
                WHERE computation_id IN ({placeholders})
            """, computation_ids_to_remove)
            remaining_secure_results = cursor.fetchone()[0]
            if remaining_secure_results > 0:
                print(f"  ⚠️  Warning: {remaining_secure_results} secure computation results still exist")
            
            cursor.execute(f"""
                SELECT COUNT(*) FROM computation_participants
                WHERE computation_id IN ({placeholders})
            """, computation_ids_to_remove)
            remaining_participants = cursor.fetchone()[0]
            if remaining_participants > 0:
                print(f"  ⚠️  Warning: {remaining_participants} computation participants still exist")
            
            try:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM computation_invitations
                    WHERE computation_id IN ({placeholders})
                """, computation_ids_to_remove)
                remaining_invitations = cursor.fetchone()[0]
                if remaining_invitations > 0:
                    print(f"  ⚠️  Warning: {remaining_invitations} computation invitations still exist")
            except sqlite3.OperationalError:
                pass
            
            # Now delete the secure computations
            try:
                cursor.execute(f"""
                    DELETE FROM secure_computations
                    WHERE computation_id IN ({placeholders})
                """, computation_ids_to_remove)
                deleted_computations = cursor.rowcount
                print(f"  Removed {deleted_computations} secure computations")
            except (sqlite3.OperationalError, sqlite3.IntegrityError) as e:
                print(f"  ❌ Error removing secure_computations: {e}")
                print(f"  This might indicate remaining references. Check the warnings above.")
                raise

        # Re-enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Commit the changes
        conn.commit()

        # Get final counts
        print("\n📊 Final Database State:")

        cursor.execute("SELECT COUNT(*) FROM secure_computations")
        final_computations = cursor.fetchone()[0]
        print(f"  Secure computations: {final_computations}")

        cursor.execute("SELECT COUNT(*) FROM computation_results")
        final_results = cursor.fetchone()[0]
        print(f"  Computation results: {final_results}")

        cursor.execute("SELECT COUNT(*) FROM secure_computation_results")
        final_secure_results = cursor.fetchone()[0]
        print(f"  Secure computation results: {final_secure_results}")

        cursor.execute("SELECT COUNT(*) FROM computation_participants")
        final_participants = cursor.fetchone()[0]
        print(f"  Computation participants: {final_participants}")

        # Try to get final counts for optional tables
        try:
            cursor.execute("SELECT COUNT(*) FROM computation_patient_records")
            final_patient_records = cursor.fetchone()[0]
            print(f"  Computation patient records: {final_patient_records}")
        except sqlite3.OperationalError:
            final_patient_records = 0

        try:
            cursor.execute("SELECT COUNT(*) FROM variable_column_mappings")
            final_mappings = cursor.fetchone()[0]
            print(f"  Variable column mappings: {final_mappings}")
        except sqlite3.OperationalError:
            final_mappings = 0

        # Calculate removed counts
        removed_computations = initial_computations - final_computations
        removed_results = initial_results - final_results
        removed_secure_results = initial_secure_results - final_secure_results
        removed_participants = initial_participants - final_participants
        removed_patient_records = initial_patient_records - final_patient_records
        removed_mappings = initial_mappings - final_mappings

        print("\n✅ Cleanup Summary:")
        print(f"  Computations removed: {removed_computations}")
        print(f"  Results removed: {removed_results}")
        print(f"  Secure results removed: {removed_secure_results}")
        print(f"  Participants removed: {removed_participants}")
        if initial_patient_records > 0:
            print(f"  Patient records removed: {removed_patient_records}")
        if initial_mappings > 0:
            print(f"  Variable mappings removed: {removed_mappings}")
        print(f"  Backup created: {backup_name}")

        # Check database size
        db_size = os.path.getsize(db_path) / 1024 / 1024  # MB
        print(f"  Database size: {db_size:.2f} MB")

        # Verify organizations are intact
        cursor.execute("SELECT COUNT(*) FROM organizations")
        org_count = cursor.fetchone()[0]
        print(f"  Organizations preserved: {org_count}")

    except Exception as e:
        print(f"❌ Error during cleanup: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

    print("\n🎯 Computation cleanup completed successfully!")

def main():
    """Main cleanup function."""
    print("🚀 Starting Comprehensive Cleanup")
    print("=" * 60)

    for db_path in DB_PATHS:
        cleanup_old_files(db_path)
        cleanup_old_computations(db_path)

    print("\n🎉 All cleanup operations completed!")
    print("💡 Note: User accounts and other important data have been preserved.")
    print("🔒 Database backups created for safety.")

if __name__ == "__main__":
    main()
