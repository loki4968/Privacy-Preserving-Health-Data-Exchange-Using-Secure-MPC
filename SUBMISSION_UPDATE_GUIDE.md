# Submission Update Guide

## ✅ **Problem Fixed: Duplicate Submission Error**

### **Previous Behavior:**
- ❌ Error: "You have already uploaded data for this computation. Each organization can only submit data once."
- ❌ No way to update or replace existing submissions
- ❌ Had to create a new computation to submit different data

### **New Behavior:**
- ✅ **Automatic Update**: If you upload again, the system automatically deletes your old submission and replaces it with the new one
- ✅ **No Error**: You can now upload CSV files multiple times for the same computation
- ✅ **Clean Replacement**: Old patient records are also deleted when you update

---

## 🔄 **How It Works Now**

1. **First Upload**: 
   - Upload CSV → Data is stored
   - Submission is recorded

2. **Second Upload (Update)**:
   - Upload new CSV → System detects existing submission
   - **Automatically deletes** old submission and patient records
   - **Stores new data** from the new CSV
   - ✅ **No error!**

---

## 📝 **What Happens When You Update**

When you upload a CSV file for a computation you've already submitted to:

1. ✅ System detects your existing submission
2. ✅ Deletes old `ComputationResult` record
3. ✅ Deletes old `ComputationPatientRecord` records (patient data)
4. ✅ Processes and stores new CSV data
5. ✅ Creates new submission record
6. ✅ Success! Your data is updated

---

## 🎯 **Use Cases**

### **Scenario 1: Corrected Data**
- You uploaded a CSV with errors
- **Solution**: Just upload the corrected CSV file
- **Result**: Old data is replaced with corrected data

### **Scenario 2: Additional Data**
- You want to add more patients to your submission
- **Solution**: Upload a new CSV with all patients (old + new)
- **Result**: Complete dataset replaces the old one

### **Scenario 3: Different Columns**
- You want to analyze different columns
- **Solution**: Upload CSV with different column selection
- **Result**: New columns replace old ones

---

## ⚠️ **Important Notes**

1. **No Undo**: Once you upload a new CSV, the old data is permanently deleted
2. **Computation Status**: If computation was already executed, you may need to re-run it after updating data
3. **Other Participants**: Your update doesn't affect other participants' submissions

---

## 🚀 **How to Update Your Submission**

1. Go to the computation details page
2. Click "Upload CSV" (same as before)
3. Select your new/updated CSV file
4. Click "Upload"
5. ✅ **Done!** Your data is automatically updated

**No need to:**
- ❌ Delete the computation
- ❌ Create a new computation
- ❌ Contact support
- ❌ Manually delete old data

---

## 🔍 **Technical Details**

### **What Gets Deleted:**
- `ComputationResult` record for your organization
- `ComputationPatientRecord` records for your organization
- All associated patient data

### **What Gets Created:**
- New `ComputationResult` record
- New `ComputationPatientRecord` records from new CSV
- Updated submission timestamp

### **What Stays:**
- Computation itself
- Other participants' submissions
- Computation configuration
- Invitations and participants list

---

## ✅ **Summary**

**Before:** One submission per organization → Error if you try again  
**After:** Multiple submissions allowed → Old data automatically replaced with new data

**You can now freely update your CSV submissions without errors!** 🎉

