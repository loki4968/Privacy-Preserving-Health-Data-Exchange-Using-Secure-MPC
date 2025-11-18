# Advanced Computation Guide

## Quick Start: Running Advanced Computations

### Step 1: Prepare Your CSV Data

Choose the appropriate CSV template from `sample_data/` folder based on your computation type:

| Computation Type | CSV Template | Description |
|-----------------|--------------|-------------|
| **Basic Statistics** | `basic_health_metrics.csv` | Heart rate, BP, temperature, glucose |
| **Correlation Analysis** | `correlation_analysis.csv` | BMI, cholesterol, exercise correlation |
| **Cohort Analysis** | `cohort_analysis.csv` | Treatment groups, outcomes, demographics |
| **Drug Safety** | `drug_safety_monitoring.csv` | Adverse events, dosages, severity |
| **Survival Analysis** | `survival_analysis.csv` | Survival times, events, risk scores |
| **Anomaly Detection** | `anomaly_detection.csv` | Time-series vitals for outliers |
| **Regression** | `regression_analysis.csv` | Multi-variable risk prediction |

### Step 2: Upload Data to Platform

1. **Login** to your organization account
2. **Navigate** to Dashboard → Data Upload
3. **Select** your CSV file
4. **Choose** data category (e.g., "Vital Signs", "Lab Results")
5. **Upload** and wait for processing confirmation

### Step 3: Create Secure Computation

1. **Go to** "Secure Computations" page
2. **Click** "New Computation" button
3. **Select Computation Type** from categories below

---

## 18 Advanced Computation Types

### 📊 Category 1: Advanced Statistical Analysis

#### 1. **Secure Correlation**
- **Use Case:** Find relationships between variables (e.g., BMI vs cholesterol)
- **CSV:** `correlation_analysis.csv`
- **How to Select:**
  - Computation Type: `secure_correlation`
  - Security Method: `Hybrid (HE + SMPC)`
- **Expected Results:** Correlation coefficient, p-value, scatter plot

#### 2. **Secure Regression**
- **Use Case:** Predict outcomes from multiple variables
- **CSV:** `regression_analysis.csv`
- **How to Select:**
  - Computation Type: `secure_regression`
  - Security Method: `Hybrid`
- **Expected Results:** Coefficients, R-squared, predictions

#### 3. **Secure Survival Analysis**
- **Use Case:** Kaplan-Meier survival curves
- **CSV:** `survival_analysis.csv`
- **How to Select:**
  - Computation Type: `secure_survival`
  - Security Method: `Hybrid`
- **Expected Results:** Survival curves, median survival time

---

### 🤖 Category 2: Machine Learning

#### 4. **Federated Logistic Regression**
- **Use Case:** Binary classification (disease/no disease)
- **CSV:** `cohort_analysis.csv` (outcome as binary)
- **How to Select:**
  - Computation Type: `federated_logistic`
  - Participants: 2+ organizations
- **Expected Results:** Model accuracy, feature importance

#### 5. **Federated Random Forest**
- **Use Case:** Complex classification with ensemble
- **CSV:** `regression_analysis.csv`
- **How to Select:**
  - Computation Type: `federated_random_forest`
  - Participants: 3+ organizations recommended
- **Expected Results:** Forest accuracy, variable importance

#### 6. **Anomaly Detection**
- **Use Case:** Detect outlier measurements
- **CSV:** `anomaly_detection.csv`
- **How to Select:**
  - Computation Type: `anomaly_detection`
  - Threshold: Auto or Custom
- **Expected Results:** Anomalies flagged, scores

---

### 🏥 Category 3: Healthcare Analytics

#### 7. **Cohort Analysis**
- **Use Case:** Compare treatment groups without revealing patients
- **CSV:** `cohort_analysis.csv`
- **How to Select:**
  - Computation Type: `cohort_analysis`
  - Groups: Define cohorts (e.g., Treatment A vs B)
- **Expected Results:** Group statistics, comparisons

#### 8. **Drug Safety Monitoring**
- **Use Case:** Detect adverse drug reactions across organizations
- **CSV:** `drug_safety_monitoring.csv`
- **How to Select:**
  - Computation Type: `drug_safety`
  - Drug Name: Specify medication
- **Expected Results:** Adverse event rates, severity distribution

#### 9. **Epidemiological Surveillance**
- **Use Case:** Population health trends
- **CSV:** `basic_health_metrics.csv` (with dates)
- **How to Select:**
  - Computation Type: `epidemiological`
  - Time Window: Specify period
- **Expected Results:** Trend analysis, geographic patterns

---

## Step-by-Step: Creating a Computation

### Example: Correlation Analysis (BMI vs Cholesterol)

**Step 1: Prepare Data**
```csv
patient_id,bmi,cholesterol_total
P001,24.5,180
P002,26.8,195
P003,23.2,175
```

**Step 2: Navigate to Wizard**
- Dashboard → Secure Computations → "New Computation"

**Step 3: Configure Computation**
1. **Computation Name:** "BMI-Cholesterol Correlation Study"
2. **Type:** Select "Secure Correlation" from dropdown
3. **Security Method:** Choose "Hybrid (HE + SMPC)"
4. **Invite Organizations:**
   - Search and select partner hospitals
   - Minimum 2 organizations for SMPC
5. **Click:** "Create Computation"

**Step 4: Submit Your Data**
- Go to computation page
- Click "Submit Data"
- Upload `correlation_analysis.csv`
- Confirm submission

**Step 5: Wait for Results**
- Other orgs submit their data
- System automatically computes when all submitted
- View results with visualizations

**Step 6: View Results**
- Correlation coefficient (e.g., 0.78)
- P-value (statistical significance)
- Scatter plot visualization
- Confidence intervals

---

## Data Format Requirements

### General Rules
✅ **Required Columns:**
- `patient_id` (unique identifier)
- At least one numeric column for analysis

✅ **Supported Types:**
- Numeric: integers, floats
- Categorical: strings (for grouping)
- Dates: YYYY-MM-DD format

❌ **Avoid:**
- Personal identifiers (SSN, names)
- Missing patient_id
- Non-numeric values in numeric columns

### Column Naming Conventions

**Use these exact names for auto-detection:**
- `heart_rate` → Beats per minute
- `blood_pressure_systolic` → Systolic BP (mmHg)
- `blood_pressure_diastolic` → Diastolic BP (mmHg)
- `temperature` → Body temp (Celsius)
- `glucose_level` → Blood glucose (mg/dL)
- `bmi` → Body Mass Index
- `cholesterol_total` → Total cholesterol

---

## Security & Privacy

### Privacy Budget
- Each computation consumes epsilon (ε) budget
- Default limit: 10.0 ε per 24 hours
- Check remaining: Dashboard → Privacy Budget

### Data Security
- **Data never leaves your org unencrypted**
- **Homomorphic Encryption:** Compute on encrypted data
- **SMPC:** Distributed computation, no single party sees raw data
- **Results only:** Aggregates revealed, not individual records

---

## Troubleshooting

### "Privacy Budget Exceeded"
**Solution:** Wait 24 hours or contact admin for reset

### "Invalid medical value"
**Problem:** Value outside plausible range
**Solution:** Check data (e.g., heart rate 300 is invalid)

### "Insufficient participants"
**Problem:** SMPC requires 2+ organizations
**Solution:** Invite more organizations or use Homomorphic Encryption

### "Computation failed"
**Problem:** Data format mismatch
**Solution:** Verify CSV matches template, check column names

---

## Best Practices

1. **Start Small:** Test with basic_health_metrics.csv first
2. **Validate Data:** Use medical range validation
3. **Invite Partners:** SMPC needs 2+ orgs for maximum security
4. **Check Budget:** Monitor epsilon consumption
5. **Document:** Add computation description for future reference

---

## Support
- **Sample Data:** `/sample_data/` folder
- **Documentation:** `SECURITY_IMPROVEMENTS.md`
- **Issues:** GitHub repository
