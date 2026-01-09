# Computation Types Testing Guide

## ✅ **ML (Machine Learning) Status: YES, Working!**

Your project **DOES support Machine Learning** computations:
- ✅ **Federated Logistic Regression** - Train ML models across organizations
- ✅ **Federated Random Forest** - Ensemble learning models
- ✅ **Anomaly Detection** - Detect outliers and unusual patterns

## 📊 **All Available Computation Types (18 Total)**

### **1. Basic Statistics (6 types)**
| Type | Description | CSV Columns | Security | Min Participants |
|------|-------------|-------------|----------|------------------|
| `average` | Calculate mean | Any numeric column | standard/homomorphic | 1 |
| `sum` | Calculate total | Any numeric column | standard/homomorphic | 1 |
| `count` | Count records | Any column | standard | 1 |
| `secure_average` | Privacy-preserving average | Any numeric column | homomorphic | 1 |
| `secure_sum` | Privacy-preserving sum | Any numeric column | homomorphic | 1 |
| `secure_variance` | Calculate variance | Any numeric column | homomorphic | 1 |

### **2. Advanced Statistics (3 types)**
| Type | Description | CSV Columns | Security | Min Participants |
|------|-------------|-------------|----------|------------------|
| `secure_correlation` | Correlation between 2 variables | 2 numeric columns | hybrid | 2 |
| `secure_regression` | Linear regression | Features + target | hybrid | 2 |
| `secure_survival` | Survival analysis | Time + event + groups | hybrid | 2 |

### **3. Machine Learning (3 types)** ⭐
| Type | Description | CSV Columns | Security | Min Participants |
|------|-------------|-------------|----------|------------------|
| `federated_logistic` | Logistic regression ML model | Features + binary target | hybrid | 3 |
| `federated_random_forest` | Random forest ML model | Features + target | hybrid | 3 |
| `anomaly_detection` | Detect outliers | Multiple numeric columns | hybrid | 2 |

### **4. Clinical Analysis (2 types)**
| Type | Description | CSV Columns | Security | Min Participants |
|------|-------------|-------------|----------|------------------|
| `cohort_analysis` | Patient cohort comparison | Demographics + outcomes | hybrid | 2 |
| `categorical_filter` | Filter patients by criteria | Any columns | homomorphic | 1 |

### **5. Pharmacovigilance (1 type)**
| Type | Description | CSV Columns | Security | Min Participants |
|------|-------------|-------------|----------|------------------|
| `drug_safety` | Adverse drug reaction detection | Drug + patient data | hybrid | 2 |

### **6. Public Health (1 type)**
| Type | Description | CSV Columns | Security | Min Participants |
|------|-------------|-------------|----------|------------------|
| `epidemiological` | Disease pattern analysis | Demographics + diagnosis + date | hybrid | 2 |

### **7. Genomics (1 type)**
| Type | Description | CSV Columns | Security | Min Participants |
|------|-------------|-------------|----------|------------------|
| `secure_gwas` | Genome-wide association study | Genetic variants + phenotype | hybrid | 3 |

### **8. Precision Medicine (1 type)**
| Type | Description | CSV Columns | Security | Min Participants |
|------|-------------|-------------|----------|------------------|
| `pharmacogenomics` | Drug-gene interaction analysis | Gene variants + drug response | hybrid | 2 |

---

## 🧪 **Testing Each Computation Type**

### **Test File: `test_computation_types.csv`**

This file contains sample data with all necessary columns for testing different computation types.

### **How to Test:**

1. **Upload the CSV file** when creating a computation
2. **Use the prompts below** to trigger different computation types
3. **The system will automatically select** the appropriate computation type based on your prompt

---

## 📝 **Test Prompts for Each Type**

### **Basic Statistics**

#### Average
```
Title: Average Patient Age
Prompt: "Calculate the average age of all patients"
Expected Type: secure_average or average
CSV Columns: Age
```

#### Sum
```
Title: Total Blood Sugar Levels
Prompt: "What is the total sum of blood sugar levels across all patients?"
Expected Type: secure_sum or sum
CSV Columns: Blood_Sug
```

#### Variance
```
Title: Blood Sugar Variability
Prompt: "Calculate the variance in blood sugar levels"
Expected Type: secure_variance
CSV Columns: Blood_Sug
```

### **Advanced Statistics**

#### Correlation
```
Title: Age vs Blood Sugar Correlation
Prompt: "How are age and blood sugar related?"
OR
Prompt: "Correlation between age and blood sugar"
Expected Type: secure_correlation
CSV Columns: Age, Blood_Sug
Security: hybrid
Min Participants: 2
```

#### Regression
```
Title: Predict Blood Sugar from Age
Prompt: "Predict blood sugar using age"
OR
Prompt: "Can age predict blood sugar?"
Expected Type: secure_regression
CSV Columns: Age (feature), Blood_Sug (target)
Security: hybrid
Min Participants: 2
```

#### Survival Analysis
```
Title: Cancer Survival Analysis
Prompt: "Survival rates for cancer patients"
OR
Prompt: "How long do cancer patients survive?"
Expected Type: secure_survival
CSV Columns: Survival_Months, Event_Occurred, Treatment_Type
Security: hybrid
Min Participants: 2
```

### **Machine Learning** ⭐

#### Federated Logistic Regression
```
Title: Diabetes Prediction Model
Prompt: "Train model to predict diabetes"
OR
Prompt: "Machine learning for diabetes prediction"
Expected Type: federated_logistic
CSV Columns: Age, BMI, Blood_Sug (features), Diagnosis (target - binary: Diabetes/Not)
Security: hybrid
Min Participants: 3
```

#### Federated Random Forest
```
Title: Heart Disease Risk Prediction
Prompt: "Random forest model for heart disease"
OR
Prompt: "Predict heart disease using random forest"
Expected Type: federated_random_forest
CSV Columns: Age, BP_Systolic, BP_Diastolic, Cholesterol (features), Diagnosis (target)
Security: hybrid
Min Participants: 3
```

#### Anomaly Detection
```
Title: Detect Abnormal Vital Signs
Prompt: "Find abnormal patients"
OR
Prompt: "Detect unusual vital signs"
Expected Type: anomaly_detection
CSV Columns: Heart_Rate, BP_Systolic, Temperature
Security: hybrid
Min Participants: 2
```

### **Clinical Analysis**

#### Cohort Analysis
```
Title: Patient Cohort Analysis
Prompt: "Compare patient groups"
OR
Prompt: "Cohort analysis by diagnosis"
Expected Type: cohort_analysis
CSV Columns: Age, Diagnosis, Treatment_Type, Outcome
Security: hybrid
Min Participants: 2
```

#### Categorical Filter (Current Working Type)
```
Title: High Blood Sugar Patients
Prompt: "List all patients with blood sugar level higher than 130"
Expected Type: categorical_filter
CSV Columns: Blood_Sug, Age, Gender
Security: homomorphic
Min Participants: 1
```

### **Pharmacovigilance**

#### Drug Safety
```
Title: Adverse Drug Reaction Detection
Prompt: "Drug safety analysis"
OR
Prompt: "Find adverse drug reactions"
Expected Type: drug_safety
CSV Columns: Age, Drug_Name, Days_on_Medication, Adverse_Event
Security: hybrid
Min Participants: 2
```

### **Public Health**

#### Epidemiological Analysis
```
Title: Disease Outbreak Analysis
Prompt: "Analyze disease outbreak across regions"
OR
Prompt: "Disease patterns in different areas"
OR
Prompt: "How is the disease spreading?"
Expected Type: epidemiological
CSV Columns: Age, Diagnosis, Region, Date
Security: hybrid
Min Participants: 2
```

---

## ⚠️ **Why It Might Always Select `categorical_filter`**

The system uses an **LLM (Large Language Model)** to interpret your prompt and select the computation type. If it's always selecting `categorical_filter`, it might be because:

1. **Your prompts are filter-like**: "List patients with X" → triggers `categorical_filter`
2. **LLM interpretation**: The prompt interpreter might be defaulting to filters
3. **Missing context**: The LLM needs clear keywords to identify computation types

### **Solution: Use Specific Keywords**

To trigger different computation types, use these keywords in your prompts:

- **Average/Mean**: "average", "mean", "calculate average"
- **Correlation**: "correlation", "relationship between", "correlate"
- **Regression**: "predict", "regression", "model", "forecast"
- **Machine Learning**: "train model", "machine learning", "ML model", "predict using ML"
- **Survival**: "survival", "survival rate", "Kaplan-Meier"
- **Anomaly**: "anomaly", "outlier", "abnormal", "unusual"
- **Cohort**: "cohort", "compare groups", "cohort analysis"

---

## 🎯 **Quick Test Checklist**

Use this checklist to verify all computation types work:

- [ ] **Basic Statistics**: Average, Sum, Variance
- [ ] **Advanced Statistics**: Correlation, Regression, Survival
- [ ] **Machine Learning**: Logistic Regression, Random Forest, Anomaly Detection
- [ ] **Clinical**: Cohort Analysis, Categorical Filter
- [ ] **Pharmacovigilance**: Drug Safety
- [ ] **Public Health**: Epidemiological
- [ ] **Genomics**: GWAS (if you have genetic data)
- [ ] **Precision Medicine**: Pharmacogenomics (if you have genetic data)

---

## 📋 **Example Test Workflow**

1. **Create Computation** with prompt: "Calculate the average age of all patients"
2. **Upload CSV** with `Age` column
3. **Submit data** from 1+ participants
4. **Execute computation**
5. **Check result** - should show average age
6. **Verify computation type** in the result - should be `secure_average` or `average`

Repeat for each computation type using the prompts above!

---

## 🔍 **Verifying Computation Type Selection**

After creating a computation, check:
1. **Computation Details Page** - shows the selected computation type
2. **API Response** - `computation.type` field
3. **Result JSON** - `computation_type` field in results

If the wrong type is selected, try rephrasing your prompt with more specific keywords.

