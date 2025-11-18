# Step-by-Step Tutorial: Your First Advanced Computation

## Tutorial 1: Correlation Analysis (15 minutes)

### What You'll Learn
- Upload CSV data
- Create a secure computation
- Invite partner organizations
- View correlation results with charts

### What You'll Need
- ✅ Account on the platform (Hospital, Clinic, or Lab)
- ✅ File: `correlation_analysis.csv`
- ✅ At least 1 partner organization (for SMPC)

---

## Step 1: Login to Platform (2 min)

1. Open browser: `http://localhost:3000` (or your deployment URL)
2. Click **"Login"**
3. Enter credentials:
   - Email: `your-hospital@example.com`
   - Password: `your-password`
4. Click **"Sign In"**

**✓ Success:** You should see the Dashboard

---

## Step 2: Upload Your Data (3 min)

### A. Navigate to Upload Page
1. Click **"Dashboard"** in navigation
2. Click **"Upload Data"** button (top right)
3. Or use direct link: `/dashboard` → Upload section

### B. Select File
1. Click **"Choose File"** or drag-and-drop
2. Select `correlation_analysis.csv` from `sample_data/` folder
3. Preview should show:
   ```
   patient_id | bmi  | cholesterol_total | ...
   P001       | 24.5 | 180              | ...
   P002       | 26.8 | 195              | ...
   ```

### C. Configure Upload
1. **Category:** Select "Lab Results"
2. **Description:** "BMI and Cholesterol Data - Q1 2024"
3. **Security Level:** Keep default "Encrypted"

### D. Upload
1. Click **"Upload Data"**
2. Wait for green checkmark: ✓ "Upload Successful"
3. Note the upload ID (e.g., `upload_abc123`)

**✓ Success:** File uploaded and encrypted

---

## Step 3: Create Secure Computation (5 min)

### A. Navigate to Computations
1. Click **"Secure Computations"** in sidebar
2. Click **"New Computation"** button (green, top right)

### B. Fill Computation Details

**Wizard - Step 1: Basic Info**
```
Computation Name: BMI-Cholesterol Correlation Study
Description: Analyzing relationship between BMI and total cholesterol
```
Click **"Next"**

**Wizard - Step 2: Select Type**
```
Category: Advanced Statistical Analysis
Computation Type: Secure Correlation ⚡
Security Method: Hybrid (HE + SMPC) [Recommended]
```
Click **"Next"**

**Wizard - Step 3: Invite Organizations**
```
Search for organizations...
☑ City General Hospital
☑ Regional Medical Center
☐ University Hospital (optional)

Minimum participants: 2 (including you)
```
Click **"Next"**

**Wizard - Step 4: Review**
```
Review all settings
Estimated Privacy Budget Cost: 0.5 ε
Current Budget: 9.5 ε remaining
```
Click **"Create Computation"**

**✓ Success:** Computation created, ID shown (e.g., `comp_xyz789`)

---

## Step 4: Submit Your Data (2 min)

### A. Go to Computation Page
- You'll be automatically redirected
- Or navigate: Secure Computations → Click your computation

### B. Submit Data
1. Click **"Submit Data"** button
2. **Select Upload:** Choose your previous upload (`upload_abc123`)
   - Or upload new CSV directly here
3. **⚠️ CRITICAL: Configure Column Mapping**
   ```
   Has Header: True
   Delimiter: ,
   Multiple Columns: bmi,cholesterol_total
   ```
   **Why?** CSV contains `patient_id` column (text like "P001") which cannot be converted to numbers!
   
4. **Confirm Submission**
   - Review data summary
   - Click **"Submit"**

### C. Wait for Partners
**Status Panel shows:**
```
✓ Your Organization: Data Submitted
⏳ City General Hospital: Waiting...
⏳ Regional Medical Center: Waiting...
```

**Note:** Computation starts automatically when all orgs submit data

---

## Step 5: View Results (3 min)

### When Computation Completes

**Status changes to:** ✅ **Completed**

### A. View Statistical Summary
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Correlation Analysis Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Correlation Coefficient: 0.78
P-Value: < 0.001 ⭐
Confidence Interval: [0.65, 0.87]

Interpretation: Strong positive correlation
✓ Statistically significant
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### B. View Visual Analysis Tab
1. Click **"Visual Analysis"** tab
2. See interactive charts:
   - **Scatter Plot:** BMI vs Cholesterol
   - **Trend Line:** Shows correlation
   - **Distribution:** Histograms for each variable

### C. Export Results
1. Click **"Export Results"** button
2. Choose format: PDF or JSON
3. Download to your computer

**✓ Tutorial Complete!** 🎉

---

## Tutorial 2: Cohort Analysis (20 minutes)

### Scenario
Compare outcomes between Treatment A, Treatment B, and Control group across multiple hospitals.

### Step 1: Prepare Data
Use `cohort_analysis.csv` which includes:
- Patient demographics
- Treatment groups
- Outcomes
- Time to outcome

### Step 2: Create Computation
1. **Type:** Cohort Analysis
2. **Groups to Compare:**
   - Treatment_A
   - Treatment_B
   - Control
3. **Outcome Variable:** `outcome`

### Step 3: Configure Analysis
**In wizard settings:**
```
Primary Outcome: outcome (Improved/Stable/Deteriorated)
Stratify By: age_group (optional)
Follow-up Period: 90 days
Statistical Test: Chi-square
```

### Step 4: View Results
**Expected output:**
```
Treatment A:  85% improved (17/20)
Treatment B:  78% improved (15/20)
Control:      45% improved (9/20)

Chi-square: 12.5, p < 0.01 ⭐
Conclusion: Treatment A significantly better than control
```

**Charts:**
- Bar chart: Outcome distribution by group
- Kaplan-Meier: Time to improvement curves

---

## Tutorial 3: Drug Safety Monitoring (25 minutes)

### Scenario
Monitor adverse events for DrugX across multiple healthcare facilities.

### Step 1: Upload Data
Use `drug_safety_monitoring.csv`

### Step 2: Create Computation
1. **Type:** Drug Safety
2. **Drug Name:** DrugX
3. **Endpoints:**
   - Adverse event rate
   - Severity distribution
   - Risk factors

### Step 3: Invite Participants
```
☑ Hospital A
☑ Hospital B  
☑ Hospital C
☑ Pharmaceutical Company XYZ (observer role)
```

### Step 4: Results Analysis
**Safety Dashboard shows:**
```
Total Patients: 60 (across 3 hospitals)
Adverse Events: 15 (25%)

Severity Breakdown:
• Mild:     60% (9/15)
• Moderate: 33% (5/15)
• Severe:   7%  (1/15)

Risk Factors Identified:
• Age > 60: RR = 2.3
• Dosage > 100mg: RR = 1.8
• Prior medications: RR = 1.5
```

**Visualizations:**
- Pie chart: Severity distribution
- Bar chart: Events by dosage
- Time series: Events over time

---

## Common Workflows

### Workflow 1: Multi-Site Research Study
```
1. Principal Investigator creates computation
2. Invites 5 partner hospitals
3. Each hospital uploads their data independently
4. System computes when all data received
5. All partners see aggregate results
6. No hospital sees others' raw data
```

### Workflow 2: Ongoing Monitoring
```
1. Create computation with "continuous" mode
2. Organizations upload data monthly
3. Results update automatically
4. Trend analysis shows changes over time
5. Alerts triggered for anomalies
```

### Workflow 3: Ad-Hoc Analysis
```
1. Upload historical data
2. Create computation quickly
3. Get results in minutes
4. Export for presentation
5. Archive computation
```

---

## Tips & Tricks

### 💡 Speed Tips
- **Batch Upload:** Upload multiple CSVs at once
- **Templates:** Save computation configs as templates
- **Favorites:** Star frequently used computation types
- **Keyboard Shortcuts:** `Ctrl+N` for new computation

### 🔒 Security Tips
- **Check Budget:** Monitor ε before large computations
- **Use SMPC:** Always invite 2+ orgs for maximum privacy
- **Verify Results:** Cross-check with expected ranges
- **Audit Logs:** Review who accessed your results

### 📊 Analysis Tips
- **Start Simple:** Basic stats before advanced ML
- **Visualize First:** Charts reveal patterns quickly
- **Statistical Significance:** Look for p < 0.05
- **Sample Size:** Minimum 20 patients recommended

### ⚡ Performance Tips
- **Smaller CSVs:** Split large files if possible
- **Fewer Columns:** Only include necessary variables
- **Clean Data:** Remove missing values beforehand
- **Off-Peak:** Run complex computations during low traffic

---

## Troubleshooting Guide

### Issue: "Upload Failed"
**Causes:**
- File too large (> 10MB)
- Invalid CSV format
- Missing required columns

**Solutions:**
1. Check file size: `ls -lh yourfile.csv`
2. Validate CSV: Open in Excel/LibreOffice
3. Compare with template: Match column names exactly

---

### Issue: "Computation Stuck at Waiting"
**Causes:**
- Partner hasn't submitted data
- Network issues
- System processing

**Solutions:**
1. Check status: Contact invited organizations
2. Remind partners: Send email notification
3. Wait: Large computations take 5-10 minutes

---

### Issue: "Privacy Budget Exceeded"
**Causes:**
- Too many computations in 24 hours
- Large epsilon costs

**Solutions:**
1. Check budget: Dashboard → Privacy Budget
2. Wait: Budget resets in 24 hours
3. Request increase: Contact administrator

---

### Issue: "Invalid Results"
**Causes:**
- Data format mismatch
- Insufficient sample size
- Outliers in data

**Solutions:**
1. Validate data: Check for outliers
2. Increase samples: Need 20+ patients minimum
3. Review logs: Check computation debug info

---

## Next Steps

✅ **Completed Tutorials?** Try these:
1. **Anomaly Detection:** Detect outliers in vital signs
2. **Survival Analysis:** Create Kaplan-Meier curves
3. **Federated Learning:** Train ML models across sites

📚 **Learn More:**
- Read `ADVANCED_COMPUTATION_GUIDE.md` for all 18 types
- Review `SECURITY_IMPROVEMENTS.md` for privacy details
- Check API docs for programmatic access

🚀 **Production Ready?**
- Deploy to cloud infrastructure
- Set up automated data pipelines
- Configure organizational policies
- Train staff on platform usage

---

**Questions?** Contact support or create GitHub issue
**Feedback?** We'd love to hear about your use cases!
