"""Simple check of file storage locations."""
import sqlite3
import os

# Database path
db_path = "health_data.db"

# Upload directory
upload_dir = "./uploads"

print("=" * 80)
print("FILE STORAGE LOCATIONS IN HEALTH DATA EXCHANGE")
print("=" * 80)

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check uploads table
print(f"\n1. UPLOAD DIRECTORY CONFIGURATION:")
print(f"   Base Upload Dir: {os.path.abspath(upload_dir)}")
print(f"   Directory exists: {os.path.exists(upload_dir)}")

if os.path.exists(upload_dir):
    subdirs = [d for d in os.listdir(upload_dir) if os.path.isdir(os.path.join(upload_dir, d))]
    print(f"   Subdirectories (org folders): {len(subdirs)}")
    for subdir in subdirs[:10]:
        subdir_path = os.path.join(upload_dir, subdir)
        files = os.listdir(subdir_path)
        print(f"     - Org {subdir}: {len(files)} files")

# Check database uploads
cursor.execute("SELECT COUNT(*) FROM uploads")
upload_count = cursor.fetchone()[0]
print(f"\n2. DATABASE UPLOADS:")
print(f"   Total uploads in database: {upload_count}")

if upload_count > 0:
    cursor.execute("""
        SELECT id, org_id, filename, original_filename, status, created_at 
        FROM uploads 
        ORDER BY created_at DESC 
        LIMIT 10
    """)
    uploads = cursor.fetchall()
    print(f"\n   Recent uploads:")
    for upload in uploads:
        upload_id, org_id, filename, original_filename, status, created_at = upload
        file_path = os.path.join(upload_dir, str(org_id), filename)
        file_exists = os.path.exists(file_path)
        print(f"   - ID: {upload_id}, Org: {org_id}")
        print(f"     File: {filename} (Original: {original_filename})")
        print(f"     Path: {file_path}")
        print(f"     Exists: {file_exists}, Status: {status}")
        print()

# Check organizations
cursor.execute("SELECT id, name FROM organizations LIMIT 5")
orgs = cursor.fetchall()
print(f"\n3. ORGANIZATION-SPECIFIC DIRECTORIES:")
for org_id, org_name in orgs:
    org_dir = os.path.join(upload_dir, str(org_id))
    exists = os.path.exists(org_dir)
    if exists:
        files = os.listdir(org_dir)
        print(f"   Org {org_id} ({org_name}): {len(files)} files in {org_dir}")
        for f in files[:3]:
            print(f"     - {f}")
    else:
        print(f"   Org {org_id} ({org_name}): No directory yet")

# Check report requests
print(f"\n4. REPORT FILES:")
reports_dir = "./reports"
print(f"   Reports directory: {os.path.abspath(reports_dir)}")
print(f"   Directory exists: {os.path.exists(reports_dir)}")

cursor.execute("SELECT COUNT(*) FROM report_requests WHERE report_file_path IS NOT NULL")
report_count = cursor.fetchone()[0]
print(f"   Reports with files: {report_count}")

if report_count > 0:
    cursor.execute("""
        SELECT id, report_file_path 
        FROM report_requests 
        WHERE report_file_path IS NOT NULL 
        LIMIT 5
    """)
    reports = cursor.fetchall()
    for req_id, file_path in reports:
        exists = os.path.exists(file_path) if file_path else False
        print(f"   - Request {req_id}: {file_path} (Exists: {exists})")

# Check CSV files in backend
print(f"\n5. CSV FILES IN BACKEND DIRECTORY:")
backend_dir = os.path.dirname(__file__)
csv_files = [f for f in os.listdir(backend_dir) if f.endswith('.csv')]
print(f"   Found {len(csv_files)} CSV files in backend root:")
for f in csv_files:
    full_path = os.path.join(backend_dir, f)
    size = os.path.getsize(full_path)
    print(f"   - {f} ({size} bytes)")

conn.close()

print("\n" + "=" * 80)
print("SUMMARY - FILE STORAGE STRUCTURE:")
print("=" * 80)
print(f"1. Uploaded CSV files: {os.path.abspath(upload_dir)}/<org_id>/<filename>")
print(f"   Example: ./uploads/1/data_2024.csv")
print(f"\n2. Report PDFs: {os.path.abspath(reports_dir)}/<filename>")
print(f"   Example: ./reports/report_abc123.pdf")
print(f"\n3. Database: {os.path.abspath(db_path)}")
print(f"   Stores metadata (filename, org_id, status, etc.)")
print("=" * 80)
