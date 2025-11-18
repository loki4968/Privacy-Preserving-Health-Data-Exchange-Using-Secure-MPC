"""Check where files are stored in the system."""
from models import SessionLocal, Upload, Organization, ReportRequest
import os
from config import UPLOAD_DIR

def check_file_storage():
    db = SessionLocal()
    
    print("=" * 80)
    print("FILE STORAGE LOCATIONS")
    print("=" * 80)
    
    # Check upload directory configuration
    print(f"\n1. UPLOAD DIRECTORY CONFIGURATION:")
    print(f"   Base Upload Dir: {os.path.abspath(UPLOAD_DIR)}")
    print(f"   Directory exists: {os.path.exists(UPLOAD_DIR)}")
    
    # Check uploads in database
    uploads = db.query(Upload).all()
    print(f"\n2. DATABASE UPLOADS:")
    print(f"   Total uploads in database: {len(uploads)}")
    
    if uploads:
        print(f"\n   Recent uploads:")
        for upload in uploads[:10]:
            file_path = upload.get_file_path()
            file_exists = os.path.exists(file_path)
            print(f"   - ID: {upload.id}")
            print(f"     Org ID: {upload.org_id}")
            print(f"     Filename: {upload.filename}")
            print(f"     Original: {upload.original_filename}")
            print(f"     Full Path: {file_path}")
            print(f"     File Exists: {file_exists}")
            print(f"     Status: {upload.status}")
            print(f"     Created: {upload.created_at}")
            print()
    
    # Check organization-specific directories
    print(f"\n3. ORGANIZATION-SPECIFIC DIRECTORIES:")
    orgs = db.query(Organization).all()
    for org in orgs[:5]:
        org_dir = os.path.join(UPLOAD_DIR, str(org.id))
        exists = os.path.exists(org_dir)
        if exists:
            files = os.listdir(org_dir)
            print(f"   Org {org.id} ({org.name}): {org_dir}")
            print(f"     Files: {len(files)}")
            if files:
                for f in files[:5]:
                    print(f"       - {f}")
        else:
            print(f"   Org {org.id} ({org.name}): Directory not created yet")
    
    # Check report files
    print(f"\n4. REPORT FILES:")
    reports_dir = os.path.join(os.path.dirname(UPLOAD_DIR), "reports")
    print(f"   Reports directory: {os.path.abspath(reports_dir)}")
    print(f"   Directory exists: {os.path.exists(reports_dir)}")
    
    report_requests = db.query(ReportRequest).filter(
        ReportRequest.report_file_path.isnot(None)
    ).all()
    print(f"   Reports with files: {len(report_requests)}")
    
    if report_requests:
        for req in report_requests[:5]:
            print(f"   - Request ID: {req.id}")
            print(f"     File Path: {req.report_file_path}")
            print(f"     File Exists: {os.path.exists(req.report_file_path) if req.report_file_path else False}")
            print()
    
    # Check for any CSV files in backend directory
    print(f"\n5. CSV FILES IN BACKEND DIRECTORY:")
    backend_dir = os.path.dirname(__file__)
    csv_files = [f for f in os.listdir(backend_dir) if f.endswith('.csv')]
    print(f"   Found {len(csv_files)} CSV files:")
    for f in csv_files:
        full_path = os.path.join(backend_dir, f)
        size = os.path.getsize(full_path)
        print(f"   - {f} ({size} bytes)")
    
    db.close()
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print(f"Files are stored in organization-specific subdirectories:")
    print(f"  Pattern: {UPLOAD_DIR}/<org_id>/<filename>")
    print(f"  Example: {UPLOAD_DIR}/1/uploaded_file.csv")
    print(f"\nReport files are stored in: ./reports/")
    print("=" * 80)

if __name__ == "__main__":
    check_file_storage()
