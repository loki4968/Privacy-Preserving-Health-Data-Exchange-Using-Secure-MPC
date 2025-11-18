# Sample Data Files for Advanced Computations

This folder contains CSV templates for all 18 advanced computation types supported by the Privacy-Preserving Health Data Exchange platform.

## 📁 Available CSV Templates

| File Name | Computation Type | Records | Use Case |
|-----------|-----------------|---------|----------|
| `basic_health_metrics.csv` | Secure Average, Sum, Variance | 20 | Basic vital signs analysis |
| `correlation_analysis.csv` | Secure Correlation | 20 | BMI vs Cholesterol relationship |
| `cohort_analysis.csv` | Cohort Analysis | 20 | Treatment effectiveness comparison |
| `drug_safety_monitoring.csv` | Drug Safety | 20 | Adverse event detection |
| `survival_analysis.csv` | Survival Analysis | 20 | Kaplan-Meier survival curves |
| `anomaly_detection.csv` | Anomaly Detection | 20 | Outlier detection in time-series |
| `regression_analysis.csv` | Secure Regression | 20 | Multi-variable risk prediction |

## 🚀 Quick Start

### 1. Choose Your Analysis

**For Basic Statistics:**
```bash
Use: basic_health_metrics.csv
Computations: secure_average, secure_sum, secure_variance
Example: Average heart rate across hospitals
```

**For Relationships Between Variables:**
```bash
Use: correlation_analysis.csv
Computations: secure_correlation
Example: Does BMI correlate with cholesterol?
```

**For Treatment Comparisons:**
```bash
Use: cohort_analysis.csv
Computations: cohort_analysis
Example: Treatment A vs Treatment B outcomes
```

**For Safety Monitoring:**
```bash
Use: drug_safety_monitoring.csv
Computations: drug_safety
Example: Adverse events for DrugX
```

### 2. Modify Templates (Optional)

You can edit these CSVs to match your real data:

```csv
# Keep the same column names
# Change patient IDs to your format
# Update values to your actual measurements
# Add more rows as needed
```

### 3. Upload to Platform

1. Login → Dashboard → Data Upload
2. Select CSV file
3. Choose category (Vital Signs, Lab Results, etc.)
4. Upload

### 4. Create Computation

1. Secure Computations → New Computation
2. Select type matching your CSV
3. Invite partner organizations
4. Submit your data
5. View results when computation completes

## ⚠️ **IMPORTANT: Column Mapping Required**

**All CSV files contain a `patient_id` column (text) that must be excluded!**

When uploading, you **MUST** specify which columns to use in the "Multiple Columns" field:

### **For correlation_analysis.csv:**
```
Multiple Columns: bmi,cholesterol_total
```

### **For basic_health_metrics.csv:**
```
Multiple Columns: heart_rate,blood_pressure_systolic,temperature
```

**Why?** The system expects **only numeric values**. Patient IDs like "P001" cannot be converted to numbers!

**Alternative:** Use the `*_numeric_only.csv` files which have patient_id column removed.

---

## 📊 Data Validation

All CSV files include **biologically plausible values**:

- ✅ Heart Rate: 30-250 bpm
- ✅ Blood Pressure: 60-250 systolic, 40-150 diastolic
- ✅ Temperature: 32-42°C
- ✅ Glucose: 20-600 mg/dL
- ✅ BMI: 15-50
- ✅ Cholesterol: 100-400 mg/dL

**Values outside these ranges will be rejected** for safety.

## 🔒 Privacy & Security

- **No Personal Information:** Sample data uses fake patient IDs (P001-P020)
- **HIPAA Compliant:** All data encrypted before transmission
- **Secure Computation:** No raw data sharing between organizations
- **Privacy Budget:** Each computation consumes differential privacy budget

## 💡 Examples by Use Case

### Healthcare Research
```
Use: cohort_analysis.csv
Goal: Compare treatment efficacy without sharing patient data
Organizations: Multiple hospitals contribute data
Result: Aggregate treatment outcomes
```

### Pharmaceutical Safety
```
Use: drug_safety_monitoring.csv
Goal: Detect adverse drug reactions across patient populations
Organizations: Hospitals + Pharmaceutical company
Result: Safety signal detection
```

### Population Health
```
Use: basic_health_metrics.csv
Goal: Monitor health trends across regions
Organizations: Regional health departments
Result: Epidemiological insights
```

### Clinical Trials
```
Use: survival_analysis.csv
Goal: Analyze treatment survival rates
Organizations: Multi-site clinical trial centers
Result: Kaplan-Meier curves
```

## 🛠️ Customization Guide

### Adding More Patients

```csv
# Original (20 patients)
P001,72,120,80,36.6,95
P020,75,125,83,36.8,101

# Extended (add more rows)
P021,70,118,79,36.7,98
P022,73,122,81,36.6,96
...
P100,71,119,80,36.8,97
```

### Changing Column Values

**Keep column names exactly as shown:**
```csv
✅ patient_id,heart_rate,blood_pressure_systolic
❌ patient,hr,bp_sys  # Wrong names!
```

**Modify values to match your data:**
```csv
# Template value
P001,72,120

# Your actual value
HOSP1_PAT_12345,75,118
```

### Adding Time-Series Data

For anomaly detection, add multiple rows per patient:
```csv
patient_id,visit_date,heart_rate
P001,2024-01-15,72
P001,2024-02-20,74
P001,2024-03-18,195  # Anomaly!
```

## 📈 Expected Results

### Correlation Analysis
```
Correlation Coefficient: 0.78
P-Value: < 0.001
Interpretation: Strong positive correlation
Visualization: Scatter plot with trend line
```

### Cohort Analysis
```
Treatment A: 85% improved
Treatment B: 78% improved  
Control: 45% improved
Statistical Test: Chi-square p < 0.05
Visualization: Bar chart comparison
```

### Drug Safety
```
Adverse Events: 25% of patients
Mild: 15%, Moderate: 8%, Severe: 2%
Risk Factors: Age > 60, High dosage
Visualization: Severity distribution
```

## ⚠️ Common Issues

### "Column not found"
**Problem:** CSV column names don't match template
**Solution:** Use exact column names from template

### "Invalid patient_id"
**Problem:** Patient ID too short or contains special characters
**Solution:** Use alphanumeric IDs (min 3 characters)

### "Medical value out of range"
**Problem:** Value biologically implausible (e.g., heart rate 500)
**Solution:** Check and correct values

### "Insufficient data"
**Problem:** Too few rows for meaningful analysis
**Solution:** Add more patient records (minimum 10 recommended)

## 🎓 Learning Path

**Beginner:**
1. Start with `basic_health_metrics.csv`
2. Run `secure_average` computation
3. Understand results visualization

**Intermediate:**
1. Use `correlation_analysis.csv`
2. Run `secure_correlation`
3. Interpret statistical significance

**Advanced:**
1. Use `cohort_analysis.csv` or `survival_analysis.csv`
2. Run multi-organization computations
3. Analyze complex results with ML insights

## 📞 Support

- **Full Guide:** `../ADVANCED_COMPUTATION_GUIDE.md`
- **Security Info:** `../SECURITY_IMPROVEMENTS.md`
- **Quick Start:** `../QUICK_START_SECURITY.md`

---

**Last Updated:** 2024-10-25  
**Version:** 1.0  
**Compatible With:** Privacy-Preserving Health Data Exchange v2.0+
