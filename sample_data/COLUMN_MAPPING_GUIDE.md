# CSV Column Mapping Quick Reference

## ⚠️ **Critical Information**

**All sample CSV files contain a `patient_id` column with text values (P001, P002, etc.) that cannot be converted to numbers!**

You **MUST** specify which columns to use when submitting CSV data for secure computations.

---

## 📋 **Copy-Paste Column Mappings**

### **correlation_analysis.csv**
```
Multiple Columns: bmi,cholesterol_total
```

**OR** for full analysis:
```
Multiple Columns: bmi,cholesterol_total,cholesterol_ldl,cholesterol_hdl,triglycerides,exercise_hours_per_week
```

---

### **basic_health_metrics.csv**
```
Multiple Columns: heart_rate,blood_pressure_systolic,blood_pressure_diastolic,temperature,glucose_level
```

**OR** with demographics:
```
Multiple Columns: heart_rate,blood_pressure_systolic,blood_pressure_diastolic,temperature,glucose_level,weight,age
```

---

### **cohort_analysis.csv**
```
Multiple Columns: age,days_to_outcome
```

**Note:** Text columns excluded: patient_id, diagnosis, gender, treatment_group, outcome, comorbidities

---

### **drug_safety_monitoring.csv**
```
Multiple Columns: age,days_on_medication,dosage_mg
```

**Note:** Text columns excluded: patient_id, drug_name, adverse_event, severity

---

### **survival_analysis.csv**
```
Multiple Columns: age,survival_time_months,event_occurred
```

**Note:** Text columns excluded: patient_id, diagnosis, treatment_received

---

### **anomaly_detection.csv**
```
Multiple Columns: heart_rate,blood_pressure_systolic,blood_pressure_diastolic,temperature
```

**Note:** Text columns excluded: patient_id, visit_date

---

### **regression_analysis.csv**
```
Multiple Columns: age,bmi,smoking_years,exercise_hours_weekly,cholesterol,cardiovascular_risk_score
```

**Note:** patient_id excluded

---

## 🎯 **How to Use**

### **Method 1: Standard CSV Upload**

1. Upload CSV file in secure computation wizard
2. When prompted for CSV mapping:
   - **Has Header:** `True`
   - **Delimiter:** `,` (comma)
   - **Multiple Columns:** Copy-paste from above ☝️
3. Submit

### **Method 2: Use Numeric-Only Files**

Use these files that have patient_id already removed:
- `correlation_analysis_numeric_only.csv`
- `basic_health_metrics_numeric_only.csv`

**Advantage:** No column mapping needed!

---

## 🔍 **Why Is This Necessary?**

The backend secure computation system expects **only numeric values** for mathematical operations. 

**What happens if you don't specify columns:**
1. System defaults to first column
2. First column is `patient_id` with text values "P001", "P002", etc.
3. System tries to convert "P001" to a number → **FAILS**
4. You get: `CSV upload failed (400)` error

**The fix:**
- Specify which numeric columns to use in "Multiple Columns" field
- System skips patient_id and uses only the columns you specify

---

## 📊 **Column Types by CSV**

### **correlation_analysis.csv**
| Column Name | Type | Include? |
|------------|------|----------|
| patient_id | TEXT | ❌ No |
| bmi | NUMBER | ✅ Yes |
| cholesterol_total | NUMBER | ✅ Yes |
| cholesterol_ldl | NUMBER | ✅ Yes |
| cholesterol_hdl | NUMBER | ✅ Yes |
| triglycerides | NUMBER | ✅ Yes |
| exercise_hours_per_week | NUMBER | ✅ Yes |

### **basic_health_metrics.csv**
| Column Name | Type | Include? |
|------------|------|----------|
| patient_id | TEXT | ❌ No |
| heart_rate | NUMBER | ✅ Yes |
| blood_pressure_systolic | NUMBER | ✅ Yes |
| blood_pressure_diastolic | NUMBER | ✅ Yes |
| temperature | NUMBER | ✅ Yes |
| glucose_level | NUMBER | ✅ Yes |
| weight | NUMBER | ✅ Yes |
| age | NUMBER | ✅ Yes |

### **cohort_analysis.csv**
| Column Name | Type | Include? |
|------------|------|----------|
| patient_id | TEXT | ❌ No |
| diagnosis | TEXT | ❌ No |
| age | NUMBER | ✅ Yes |
| gender | TEXT | ❌ No |
| treatment_group | TEXT | ❌ No |
| outcome | TEXT | ❌ No |
| days_to_outcome | NUMBER | ✅ Yes |
| comorbidities | TEXT | ❌ No |

### **drug_safety_monitoring.csv**
| Column Name | Type | Include? |
|------------|------|----------|
| patient_id | TEXT | ❌ No |
| drug_name | TEXT | ❌ No |
| age | NUMBER | ✅ Yes |
| adverse_event | TEXT | ❌ No |
| severity | TEXT | ❌ No |
| days_on_medication | NUMBER | ✅ Yes |
| dosage_mg | NUMBER | ✅ Yes |

---

## 💡 **Pro Tips**

### **Tip 1: Start with Two Columns**
For correlation analysis, you only need 2 columns:
```
Multiple Columns: bmi,cholesterol_total
```

### **Tip 2: Use Numeric-Only Files**
Simplest solution - no column mapping needed!
```
File: correlation_analysis_numeric_only.csv
Multiple Columns: (leave empty - auto-detects all)
```

### **Tip 3: Check Your Computation Type**
- **Correlation:** Needs 2+ columns
- **Regression:** Needs 3+ columns (multiple predictors)
- **Average/Sum:** Can use 1 column

### **Tip 4: Exclude Non-Numeric Columns**
**Never include these types:**
- Patient IDs (P001, P002)
- Dates (2024-01-15)
- Diagnoses (Diabetes, Hypertension)
- Text labels (Male, Female, Treatment_A)
- Categorical data (Mild, Moderate, Severe)

---

## 🐛 **Troubleshooting**

### **Error: "No valid numeric values found"**
**Cause:** You specified a text column like patient_id
**Fix:** Use column mapping from this guide

### **Error: "Missing columns in CSV header"**
**Cause:** Typo in column name or column doesn't exist
**Fix:** Check exact column names in CSV (case-sensitive!)

### **Error: "CSV upload failed (400)"**
**Cause:** No column mapping specified, defaulted to patient_id
**Fix:** Add "Multiple Columns" as shown in this guide

---

## ✅ **Verified Working Examples**

### **Example 1: BMI-Cholesterol Correlation**
```
File: correlation_analysis.csv
Has Header: True
Delimiter: ,
Multiple Columns: bmi,cholesterol_total
Status: ✅ Works perfectly
```

### **Example 2: All Vital Signs**
```
File: basic_health_metrics.csv
Has Header: True
Delimiter: ,
Multiple Columns: heart_rate,blood_pressure_systolic,temperature
Status: ✅ Works perfectly
```

### **Example 3: Numeric-Only File**
```
File: correlation_analysis_numeric_only.csv
Has Header: True
Delimiter: ,
Multiple Columns: (empty)
Status: ✅ Works perfectly - auto-detects all columns
```

---

## 📞 **Need Help?**

If you're still getting errors:
1. ✅ Check you're using exact column names from CSV
2. ✅ Verify Has Header is set to `True`
3. ✅ Confirm delimiter is `,` (comma)
4. ✅ Make sure you're not including patient_id in Multiple Columns
5. ✅ Try numeric-only files as alternative

---

**Last Updated:** 2024-10-25  
**Issue:** CSV upload failed (400) - Patient ID column contains non-numeric text  
**Solution:** Specify numeric columns in "Multiple Columns" field
