# Detailed File Upload Flow - Frontend to Backend Storage

## Complete Journey: From User Click to Database Storage

---

## 📋 Table of Contents
1. [Overview](#overview)
2. [Frontend Flow](#frontend-flow)
3. [Backend Flow](#backend-flow)
4. [Storage Structure](#storage-structure)
5. [Code References](#code-references)
6. [Error Handling](#error-handling)

---

## Overview

This document traces the complete path of a CSV file from the moment a user uploads it through the frontend UI until it's stored on disk and recorded in the database.

**Key Components:**
- **Frontend:** Next.js React component (`UploadForm.jsx`)
- **API Layer:** FastAPI endpoint (`/upload`)
- **Storage:** File system + SQLite database
- **Security:** JWT authentication, organization isolation

---

## Frontend Flow

### Step 1: User Selects File
**Location:** `app/components/UploadForm.jsx`

```javascript
// Lines 66-75: Dropzone configuration
const { getRootProps, getInputProps, isDragActive } = useDropzone({
  onDrop,
  accept: {
    'application/json': ['.json'],
    'text/csv': ['.csv'],
    'application/vnd.ms-excel': ['.xls'],
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
  },
  multiple: true
});
```

**What Happens:**
1. User drags/drops file or clicks to browse
2. File validation (type, size) happens in browser
3. File added to `files` state array with metadata:
   ```javascript
   {
     file: File object,
     id: "random_id",
     progress: 0,
     status: 'pending'
   }
   ```

### Step 2: User Selects Category
**Location:** `app/components/UploadForm.jsx` (lines 270-294)

```javascript
// Available categories
const categories = [
  { id: 'auto', name: 'Auto-detect' },
  { id: 'blood_sugar', name: 'Blood Sugar' },
  { id: 'blood_test', name: 'Blood Test' },
  { id: 'vital_signs', name: 'Vital Signs' },
  { id: 'medical_history', name: 'Medical History' }
];
```

**User Action:** Selects category from dropdown (default: 'auto')

### Step 3: User Clicks "Upload All"
**Location:** `app/components/UploadForm.jsx` (lines 81-256)

**Process Flow:**

#### 3.1 Authentication Check
```javascript
// Lines 88-91
if (!user || !user.token) {
  toast.error('Please login first');
  return;
}
```

#### 3.2 FormData Preparation
```javascript
// Lines 101-105
const formData = new FormData();
formData.append('file', fileObj.file);
formData.append('category', selectedCategory);
```

**FormData Contents:**
- `file`: Binary file data
- `category`: Selected category (e.g., "blood_sugar", "auto")

#### 3.3 XMLHttpRequest Setup
```javascript
// Lines 115-196
const xhr = new XMLHttpRequest();
xhr.open('POST', API_ENDPOINTS.upload, true);

// Headers
xhr.setRequestHeader('Authorization', `Bearer ${user.token}`);
xhr.setRequestHeader('X-Force-Upload', 'true');

// Progress tracking
xhr.upload.onprogress = function(e) {
  if (e.lengthComputable) {
    const percentComplete = Math.round((e.loaded / e.total) * 100);
    // Update UI progress bar
  }
};

// Send request
xhr.send(formData);
```

**Request Details:**
- **URL:** `http://localhost:8000/upload`
- **Method:** POST
- **Headers:**
  - `Authorization: Bearer <JWT_TOKEN>`
  - `X-Force-Upload: true`
- **Body:** FormData with file + category

---

## Backend Flow

### Step 4: Request Arrives at Backend
**Location:** `backend/main.py` (line 291)

```python
@app.post("/upload", response_model=dict)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    category: str = Form(...),
    current_user: dict = Depends(require_permissions([Permission.WRITE_PATIENT_DATA])),
    db: Session = Depends(get_db),
):
```

**FastAPI automatically:**
- Extracts JWT token from Authorization header
- Validates token via `require_permissions` dependency
- Parses FormData into `file` and `category` parameters
- Provides database session

### Step 5: Authentication & Authorization
**Location:** `backend/main.py` (lines 299-337)

```python
# Lines 304-305: Check force upload header
force_upload = request.headers.get('X-Force-Upload', '').lower() == 'true'

# Lines 308-311: Get organization from token
org = db.query(Organization).filter_by(email=current_user["sub"]).first()
if not org:
    raise HTTPException(status_code=404, detail="Organization not found")

# Lines 314-319: Verify organization ID matches token
if str(org.id) != str(current_user.get("id")):
    raise HTTPException(status_code=403, detail="Access denied: Organization ID mismatch")

# Lines 324-329: Verify organization is active
if not org.is_active:
    raise HTTPException(status_code=403, detail="Account is not active")

# Lines 332-337: Check email verification (skipped if force_upload=true)
if not force_upload and not org.email_verified:
    raise HTTPException(status_code=403, detail="Please verify your email")
```

**Security Checks:**
✅ Valid JWT token
✅ Organization exists
✅ Organization ID matches token
✅ Organization is active
✅ Email verified (or force upload enabled)

### Step 6: File Validation
**Location:** `backend/main.py` (lines 339-358)

```python
# Lines 340-345: Validate file extension
if not allowed_file_extension(file.filename):
    raise HTTPException(status_code=400, detail="Invalid file type. Only CSV files are allowed.")

# Lines 348-354: Validate file size
if not validate_file_size(file):
    raise HTTPException(status_code=400, detail="File size too large. Maximum size is 10MB.")
```

**Validation Rules:**
- ✅ File extension: `.csv`, `.xlsx`, `.json`
- ✅ File size: Maximum 10MB
- ✅ File must not be empty

### Step 7: Directory Creation
**Location:** `backend/main.py` (lines 361-364)

```python
# Create organization-specific upload directory
org_upload_dir = os.path.join(UPLOAD_DIR, str(org.id))
os.makedirs(org_upload_dir, exist_ok=True)
print(f"Organization upload directory: {org_upload_dir}")
```

**Directory Structure Created:**
```
backend/
└── uploads/
    └── <org_id>/          # e.g., uploads/1/, uploads/4/
        └── (files will be saved here)
```

**Example:**
- Organization ID: 4
- Directory: `C:\MAIN-PROJECT\health-data-exchange\backend\uploads\4\`

### Step 8: Filename Generation
**Location:** `backend/main.py` (lines 366-371)

```python
# Create a unique filename
timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
safe_filename = f"{category}_{timestamp}_{file.filename}"
safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in "._-")
file_path = os.path.join(org_upload_dir, safe_filename)
```

**Filename Pattern:**
```
{category}_{timestamp}_{original_filename}
```

**Example:**
- Original: `blood_sugar_report.csv`
- Category: `blood_sugar`
- Timestamp: `20250827_141743`
- Result: `blood_sugar_20250827_141743_blood_sugar_report.csv`

**Full Path:**
```
C:\MAIN-PROJECT\health-data-exchange\backend\uploads\4\blood_sugar_20250827_141743_blood_sugar_report.csv
```

### Step 9: Database Entry Creation
**Location:** `backend/main.py` (lines 381-394)

```python
# Create upload entry first with pending status
upload_entry = Upload(
    filename=safe_filename,
    original_filename=file.filename,
    category=category,
    org_id=org.id,
    file_size=file_size,
    mime_type=mime_type,
    status="pending"
)
db.add(upload_entry)
db.commit()
db.refresh(upload_entry)
```

**Database Record (uploads table):**
```sql
INSERT INTO uploads (
    filename,                                    -- blood_sugar_20250827_141743_blood_sugar_report.csv
    original_filename,                           -- blood_sugar_report.csv
    category,                                    -- blood_sugar
    org_id,                                      -- 4
    file_size,                                   -- 1024 (bytes)
    mime_type,                                   -- text/csv
    status,                                      -- pending
    created_at                                   -- 2025-08-27 14:17:43
) VALUES (...);
```

**Status:** `pending` → File not yet saved to disk

### Step 10: File Saved to Disk
**Location:** `backend/main.py` (lines 396-441)

```python
# Lines 399-404: Read and save file
file_content = file.file.read()
file.file.seek(0)  # Reset file pointer

with open(file_path, "wb") as buffer:
    buffer.write(file_content)

# Lines 407-413: Verify file was saved correctly
if not os.path.exists(file_path):
    raise FileNotFoundError(f"File was not saved: {file_path}")

saved_size = os.path.getsize(file_path)
if saved_size != file_size:
    raise ValueError(f"Saved file size mismatch")
```

**File System:**
```
uploads/
└── 4/
    └── blood_sugar_20250827_141743_blood_sugar_report.csv  ✅ SAVED
```

**Encoding Detection & Conversion:**
```python
# Lines 415-441: Try multiple encodings
encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252']

for encoding in encodings:
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            file_text = f.read()
            if file_text and ',' in file_text:  # Basic CSV check
                detected_encoding = encoding
                break
    except UnicodeDecodeError:
        continue

# Convert to UTF-8 if needed
if detected_encoding != 'utf-8':
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(file_text)
```

### Step 11: Status Update to Processing
**Location:** `backend/main.py` (lines 450-452)

```python
# Update status to processing
upload_entry.status = "processing"
db.commit()
```

**Database Update:**
```sql
UPDATE uploads 
SET status = 'processing' 
WHERE id = <upload_entry.id>;
```

### Step 12: File Analysis
**Location:** `backend/main.py` (lines 454-491)

```python
# Run analysis on file
analysis_result = run_analysis(file_path, category)

if "error" in analysis_result:
    upload_entry.status = "error"
    upload_entry.error_message = analysis_result["error"]
else:
    upload_entry.status = "completed"
    upload_entry.result = analysis_result
    upload_entry.processed_at = datetime.utcnow()

db.commit()
```

**Analysis Process:**
1. Read CSV file
2. Parse data
3. Validate structure
4. Generate statistics
5. Store results in JSON format

**Database Final Update:**
```sql
UPDATE uploads 
SET 
    status = 'completed',
    result = '{"statistics": {...}, "summary": {...}}',
    processed_at = '2025-08-27 14:17:45'
WHERE id = <upload_entry.id>;
```

### Step 13: Response Sent to Frontend
**Location:** `backend/main.py` (lines 484-491)

```python
return {
    "message": "File uploaded and processed successfully",
    "result_id": upload_entry.id,
    "result": upload_entry.to_dict()
}
```

**Response JSON:**
```json
{
  "message": "File uploaded and processed successfully",
  "result_id": 8,
  "result": {
    "id": 8,
    "filename": "blood_sugar_20250827_141743_blood_sugar_report.csv",
    "original_filename": "blood_sugar_report.csv",
    "category": "blood_sugar",
    "status": "completed",
    "created_at": "2025-08-27T14:17:43",
    "processed_at": "2025-08-27T14:17:45",
    "file_size": 1024,
    "result": {
      "statistics": {...},
      "summary": {...}
    },
    "org_id": 4
  }
}
```

---

## Storage Structure

### Final Storage Layout

```
health-data-exchange/
├── backend/
│   ├── uploads/                           # Main upload directory
│   │   ├── 1/                            # Organization 1's files
│   │   │   ├── vital_signs_20250826_073258_test_upload.csv
│   │   │   └── lab_results_20250826_080000_data.csv
│   │   ├── 4/                            # Organization 4's files
│   │   │   └── blood_sugar_20250827_141743_blood_sugar_report.csv
│   │   └── 6/                            # Organization 6's files
│   │       └── blood_test_20250827_141803_cancer_reports.csv
│   │
│   └── health_data.db                    # SQLite database
│       └── uploads table                 # File metadata
│           ├── id: 1
│           ├── id: 2
│           ├── id: 8  ← Our uploaded file
│           └── ...
```

### Database Schema

```sql
CREATE TABLE uploads (
    id INTEGER PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,              -- Stored filename with timestamp
    original_filename VARCHAR(255) NOT NULL,     -- Original user filename
    category VARCHAR(50) NOT NULL,               -- blood_sugar, vital_signs, etc.
    org_id INTEGER NOT NULL,                     -- Foreign key to organizations
    file_size INTEGER NOT NULL,                  -- Size in bytes
    mime_type VARCHAR(100) NOT NULL,             -- text/csv, application/json
    status VARCHAR(20) DEFAULT 'pending',        -- pending → processing → completed/error
    result JSON,                                 -- Analysis results
    error_message VARCHAR(500),                  -- Error details if failed
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    processed_at DATETIME,
    FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
);
```

---

## Code References

### Frontend Files

| File | Lines | Purpose |
|------|-------|---------|
| `app/components/UploadForm.jsx` | 1-423 | Main upload UI component |
| `app/components/UploadForm.jsx` | 66-75 | File dropzone configuration |
| `app/components/UploadForm.jsx` | 81-256 | Upload logic with XHR |
| `app/components/UploadForm.jsx` | 101-105 | FormData preparation |
| `app/components/UploadForm.jsx` | 119-196 | XHR request setup |
| `app/config/api.js` | 1-162 | API endpoints configuration |
| `app/config/api.js` | 6 | Upload endpoint definition |

### Backend Files

| File | Lines | Purpose |
|------|-------|---------|
| `backend/main.py` | 291-518 | Upload endpoint handler |
| `backend/main.py` | 299-337 | Authentication & authorization |
| `backend/main.py` | 339-358 | File validation |
| `backend/main.py` | 361-371 | Directory & filename creation |
| `backend/main.py` | 381-394 | Database entry creation |
| `backend/main.py` | 396-441 | File saving & encoding |
| `backend/main.py` | 450-491 | Analysis & final update |
| `backend/config.py` | 62 | Upload directory configuration |
| `backend/models.py` | 86-131 | Upload model definition |
| `backend/models.py` | 119-121 | File path generation method |

---

## Error Handling

### Frontend Error Scenarios

| Error | Cause | Handling |
|-------|-------|----------|
| No token | User not logged in | Show "Please login first" |
| Network error | Backend not running | Show "Network error - check backend" |
| Upload timeout | Server unresponsive | Show "Upload timed out" (30s) |
| 400 Bad Request | Invalid file/category | Show error message from server |
| 403 Forbidden | Email not verified | Show "Please verify email" |
| 500 Server Error | Backend processing failed | Show error details |

### Backend Error Scenarios

| Error | Cause | Response |
|-------|-------|----------|
| 401 Unauthorized | Invalid/expired token | HTTP 401 + error message |
| 403 Forbidden | Email not verified | HTTP 403 + "Please verify email" |
| 404 Not Found | Organization not found | HTTP 404 + "Organization not found" |
| 400 Bad Request | Invalid file type/size | HTTP 400 + validation error |
| 500 Internal Error | File save/analysis failed | HTTP 500 + error details |

### Error Recovery

**Frontend:**
```javascript
// Lines 240-248
catch (error) {
  console.error('Upload error:', error);
  setFiles(prev =>
    prev.map(f =>
      f.id === fileObj.id ? { ...f, status: 'error', error: error.message } : f
    )
  );
  toast.error(`Failed to upload: ${error.message}`);
}
```

**Backend:**
```python
# Lines 501-511: Cleanup on error
except Exception as e:
    # Clean up file if something goes wrong
    if 'file_path' in locals() and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as cleanup_error:
            print(f"Failed to clean up file: {str(cleanup_error)}")
    raise HTTPException(status_code=500, detail=error_msg)
```

---

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 1. User selects file
                              ▼
                    ┌──────────────────┐
                    │  UploadForm.jsx  │
                    │  - File dropzone │
                    │  - Category      │
                    └──────────────────┘
                              │
                              │ 2. User clicks "Upload All"
                              ▼
                    ┌──────────────────┐
                    │  FormData prep   │
                    │  - file: Binary  │
                    │  - category: str │
                    └──────────────────┘
                              │
                              │ 3. XHR POST Request
                              │    Headers: Authorization, X-Force-Upload
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 4. Request arrives at /upload
                              ▼
                    ┌──────────────────┐
                    │  Authentication  │
                    │  - Validate JWT  │
                    │  - Get org       │
                    └──────────────────┘
                              │
                              │ 5. Security checks pass
                              ▼
                    ┌──────────────────┐
                    │  File Validation │
                    │  - Type: .csv    │
                    │  - Size: <10MB   │
                    └──────────────────┘
                              │
                              │ 6. Validation passes
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FILE SYSTEM                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 7. Create directory
                              ▼
                    uploads/<org_id>/
                              │
                              │ 8. Generate filename
                              │    {category}_{timestamp}_{original}
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATABASE (SQLite)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 9. Create DB entry (status: pending)
                              ▼
                    uploads table
                    ├── id: 8
                    ├── filename: blood_sugar_...csv
                    ├── org_id: 4
                    └── status: pending
                              │
                              │ 10. Save file to disk
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FILE SYSTEM                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        uploads/4/blood_sugar_20250827_141743_blood_sugar_report.csv
                              │
                              │ 11. Update status: processing
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ANALYSIS ENGINE                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 12. Analyze file
                              │     - Parse CSV
                              │     - Generate stats
                              ▼
                    ┌──────────────────┐
                    │  Analysis Result │
                    │  - Statistics    │
                    │  - Summary       │
                    └──────────────────┘
                              │
                              │ 13. Update DB (status: completed)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DATABASE (SQLite)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    uploads table
                    ├── id: 8
                    ├── status: completed
                    ├── result: {...}
                    └── processed_at: 2025-08-27...
                              │
                              │ 14. Send response to frontend
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ 15. Show success message
                              │ 16. Redirect to /result/{id}
                              ▼
                    ┌──────────────────┐
                    │  Results Page    │
                    │  - Statistics    │
                    │  - Charts        │
                    └──────────────────┘
```

---

## Summary

### Key Takeaways

1. **Organization Isolation**: Each organization's files stored in separate directories (`uploads/<org_id>/`)

2. **Unique Filenames**: Pattern `{category}_{timestamp}_{original_filename}` prevents conflicts

3. **Database + Filesystem**: Metadata in database, actual files on disk

4. **Three-Stage Status**:
   - `pending` → Database entry created
   - `processing` → File saved, analysis running
   - `completed` → Analysis done, results stored

5. **Security Layers**:
   - JWT authentication
   - Organization verification
   - Email verification check
   - File validation (type, size)

6. **Error Recovery**: Failed uploads cleaned up automatically

7. **Progress Tracking**: Real-time upload progress via XHR events

8. **Encoding Handling**: Automatic detection and UTF-8 conversion

---

## Quick Reference

**Upload Endpoint:** `POST http://localhost:8000/upload`

**Request:**
```
Headers:
  Authorization: Bearer <JWT_TOKEN>
  X-Force-Upload: true

Body (FormData):
  file: <binary_file_data>
  category: "blood_sugar"
```

**Response:**
```json
{
  "message": "File uploaded and processed successfully",
  "result_id": 8,
  "result": {
    "id": 8,
    "filename": "blood_sugar_20250827_141743_blood_sugar_report.csv",
    "status": "completed",
    ...
  }
}
```

**Storage Path:**
```
backend/uploads/<org_id>/<category>_<timestamp>_<original_filename>
```

**Database Record:**
```
uploads table → id, filename, org_id, status, result, created_at, processed_at
```
