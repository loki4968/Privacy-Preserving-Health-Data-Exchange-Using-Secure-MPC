# File Storage Guide - Health Data Exchange System

## Overview
This document explains where and how files are stored in the Privacy-Preserving Health Data Exchange system.

---

## Storage Locations

### 1. **Uploaded CSV Files**
**Location:** `backend/uploads/<org_id>/<filename>`

**Structure:**
```
backend/
└── uploads/
    ├── 1/              # Organization ID 1
    │   ├── vital_signs_20250826_073258_test_upload.csv
    │   └── lab_results_20250826_080000_data.csv
    ├── 2/              # Organization ID 2
    │   └── medications_20250826_090000_meds.csv
    └── 4/              # Organization ID 4
        └── auto_20250827_142106_cancer_reports.csv
```

**Key Points:**
- Each organization has its own subdirectory identified by `org_id`
- Files are renamed with a timestamp and category prefix for uniqueness
- Original filenames are preserved in the database
- Directory is created automatically when an organization uploads their first file

**Configuration:**
- Defined in: `backend/config.py` (line 62)
- Default: `./uploads`
- Can be changed via environment variable `UPLOAD_DIR`

---

### 2. **Report Files (PDFs)**
**Location:** `backend/reports/<filename>`

**Structure:**
```
backend/
└── reports/
    ├── report_abc123.pdf
    ├── report_xyz789.pdf
    └── patient_report_20250826.pdf
```

**Key Points:**
- Used for patient medical reports
- Generated when healthcare organizations approve report requests
- File paths stored in `report_requests.report_file_path` database column

---

### 3. **Database Storage**
**Location:** `backend/health_data.db`

**What's Stored:**
- **File Metadata** (in `uploads` table):
  - `id`: Upload record ID
  - `filename`: Stored filename (with timestamp)
  - `original_filename`: Original uploaded filename
  - `org_id`: Organization that uploaded the file
  - `file_size`: Size in bytes
  - `mime_type`: File type
  - `status`: Processing status (pending, completed, error)
  - `created_at`: Upload timestamp
  - `result`: Processing results (JSON)

- **Secure Computation Data** (encrypted):
  - Computation submissions
  - SMPC shares
  - Encrypted results

- **Health Records** (encrypted):
  - Patient data
  - Medical records
  - All stored as encrypted binary data

---

## File Upload Flow

### Step-by-Step Process:

1. **User uploads CSV file via frontend**
   - File sent to `/upload` endpoint
   - Authentication token validated

2. **Backend receives file**
   - Organization ID extracted from JWT token
   - File validated (size, type, format)

3. **Organization directory created**
   ```python
   org_upload_dir = os.path.join(UPLOAD_DIR, str(org.id))
   os.makedirs(org_upload_dir, exist_ok=True)
   ```

4. **File renamed and saved**
   - Pattern: `{category}_{timestamp}_{original_filename}`
   - Example: `vital_signs_20250826_073258_test_upload.csv`
   - Saved to: `uploads/{org_id}/{new_filename}`

5. **Database record created**
   - Metadata stored in `uploads` table
   - Status set to "pending"

6. **File processed**
   - Data extracted and validated
   - Encrypted if needed
   - Status updated to "completed" or "error"

---

## Code References

### File Path Generation
**File:** `backend/models.py` (lines 119-121)
```python
def get_file_path(self):
    """Get the absolute path to the uploaded file."""
    return os.path.join(UPLOAD_DIR, str(self.org_id), self.filename)
```

### Upload Directory Configuration
**File:** `backend/config.py` (lines 61-63)
```python
# File Upload
UPLOAD_DIR: str = "./uploads"
MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS: str = ".csv,.xlsx,.json"
```

### Directory Creation
**File:** `backend/main.py` (lines 362-364)
```python
# Create organization-specific upload directory
org_upload_dir = os.path.join(UPLOAD_DIR, str(org.id))
os.makedirs(org_upload_dir, exist_ok=True)
```

### File Deletion
**File:** `backend/main.py` (lines 615-617)
```python
# Delete the physical file if it exists
file_path = os.path.join(UPLOAD_DIR, upload.filename)
if os.path.exists(file_path):
    os.remove(file_path)
```

---

## Current Storage Status

### From Database Analysis:
- **Total uploads in database:** 7
- **Organization directories created:** 0 (files may have been deleted)
- **Report files:** 0
- **Test CSV files in backend root:** 3

### Example Upload Records:
```
ID: 8, Org: 4
  File: auto_20250827_142106_cancer_reports.csv
  Original: cancer_reports.csv
  Path: ./uploads/4/auto_20250827_142106_cancer_reports.csv
  Status: completed
  Exists: False (file was deleted or moved)

ID: 2, Org: 1
  File: vital_signs_20250826_074517_test_upload.csv
  Original: test_upload.csv
  Path: ./uploads/1/vital_signs_20250826_074517_test_upload.csv
  Status: completed
  Exists: False (file was deleted or moved)
```

---

## Security Considerations

### 1. **Organization Isolation**
- Each organization's files stored in separate directories
- Prevents unauthorized access to other organizations' data

### 2. **File Validation**
- Size limits enforced (10MB default)
- File type restrictions (.csv, .xlsx, .json)
- Content validation before processing

### 3. **Encryption**
- Sensitive data encrypted before storage
- Homomorphic encryption for secure computations
- SMPC shares distributed across participants

### 4. **Access Control**
- JWT authentication required
- Organization ID validated against token
- Role-based permissions enforced

---

## Maintenance & Cleanup

### Check Storage Status:
```bash
cd backend
python check_storage_simple.py
```

### Manual Cleanup:
```bash
# Remove old uploads (be careful!)
rm -rf backend/uploads/*

# Clear database records
# Use appropriate database management tools
```

### Automated Cleanup:
- Consider implementing retention policies
- Archive old files periodically
- Clean up failed/error uploads

---

## Troubleshooting

### Issue: Files not found after upload
**Possible Causes:**
1. Directory permissions issue
2. File was deleted by cleanup script
3. Database and filesystem out of sync

**Solution:**
- Check `UPLOAD_DIR` configuration
- Verify directory exists and is writable
- Check database records vs actual files

### Issue: Upload directory full
**Solution:**
1. Implement file retention policy
2. Archive old files to external storage
3. Increase storage capacity

### Issue: Organization directory not created
**Solution:**
- Check file permissions on `uploads/` directory
- Verify `os.makedirs()` call in upload endpoint
- Check server logs for errors

---

## Configuration Options

### Environment Variables:
```bash
# .env file
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=10485760  # 10MB in bytes
ALLOWED_EXTENSIONS=.csv,.xlsx,.json
```

### Change Upload Directory:
```python
# config.py
UPLOAD_DIR: str = "/var/data/health-exchange/uploads"
```

---

## Summary

**File Storage Pattern:**
```
backend/
├── uploads/
│   └── <org_id>/
│       └── <category>_<timestamp>_<original_filename>
├── reports/
│   └── <report_filename>.pdf
└── health_data.db (metadata + encrypted data)
```

**Key Takeaways:**
- ✅ Files organized by organization ID
- ✅ Automatic directory creation
- ✅ Timestamp-based unique filenames
- ✅ Database tracks all file metadata
- ✅ Secure, isolated storage per organization
- ✅ Encrypted sensitive data
