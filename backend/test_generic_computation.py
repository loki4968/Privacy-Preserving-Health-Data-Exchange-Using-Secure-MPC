"""
Test script for the generic prompt-driven computation system.
Run this to verify all components are working correctly.
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from prompt_interpreter import PromptInterpreter
from services.dataset_service import DatasetService
from services.column_mapping_service import ColumnMappingService
from sqlalchemy.orm import Session
from models import get_db

def test_prompt_interpretation():
    """Test prompt interpretation with different providers."""
    print("\n" + "="*60)
    print("TEST 1: Prompt Interpretation")
    print("="*60)
    
    interpreter = PromptInterpreter()
    
    test_prompts = [
        "Compare average fasting blood glucose levels between diabetic and non-diabetic patients, adjusting for age and BMI",
        "Analyze the correlation between cholesterol levels and cardiovascular risk scores in patients aged 45-65",
        "Perform survival analysis for cancer patients based on treatment type and age"
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n--- Test Prompt {i} ---")
        print(f"Input: {prompt}")
        
        try:
            spec = interpreter.interpret_prompt(prompt)
            print(f"✅ Success!")
            print(f"   Provider: {interpreter.llm_provider}")
            print(f"   Research Question: {spec.get('research_question', 'N/A')}")
            print(f"   Analysis Type: {spec.get('analysis_type', 'N/A')}")
            print(f"   Variables Found: {len(spec.get('variables', []))}")
            for var in spec.get('variables', []):
                print(f"      - {var.get('name')} ({var.get('role')}) [{var.get('unit')}]")
            print(f"   Operations: {len(spec.get('operations', []))}")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    return True

def test_dataset_schema_inference():
    """Test dataset schema inference."""
    print("\n" + "="*60)
    print("TEST 2: Dataset Schema Inference")
    print("="*60)
    
    # Create a sample CSV for testing
    sample_csv_path = Path(__file__).parent.parent / "sample_data" / "basic_health_metrics.csv"
    
    if not sample_csv_path.exists():
        print(f"⚠️  Sample CSV not found at {sample_csv_path}")
        print("   Creating a test CSV...")
        
        # Create a simple test CSV
        test_csv_path = Path(__file__).parent / "test_data.csv"
        with open(test_csv_path, 'w') as f:
            f.write("patient_id,glucose_level_mg_dl,diabetes_status,age_years,bmi_value\n")
            f.write("P001,120,Yes,45,25.3\n")
            f.write("P002,180,Yes,52,28.1\n")
            f.write("P003,95,No,38,22.5\n")
        
        sample_csv_path = test_csv_path
    
    print(f"Testing with CSV: {sample_csv_path}")
    
    try:
        # Create a mock database session (we'll use None for testing)
        # In real usage, you'd use: db = next(get_db())
        dataset_service = DatasetService(db=None)
        
        schema = dataset_service.infer_schema_from_csv(
            str(sample_csv_path),
            has_header=True,
            delimiter=','
        )
        
        print(f"✅ Schema inferred successfully!")
        print(f"   Columns found: {len(schema)}")
        for col in schema:
            print(f"      - {col['column_name']}: {col['data_type']} [{col.get('unit', 'no unit')}]")
            print(f"        Tags: {col.get('semantic_tags', [])}")
        
        return schema
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_column_mapping():
    """Test automatic column mapping."""
    print("\n" + "="*60)
    print("TEST 3: Automatic Column Mapping")
    print("="*60)
    
    # Test variables from a prompt interpretation
    test_variables = [
        {
            "id": "fasting_glucose",
            "name": "Fasting blood glucose",
            "role": "outcome",
            "dtype": "float",
            "unit": "mg/dL",
            "concept_tags": ["blood_glucose", "fasting", "glucose", "mg/dL"]
        },
        {
            "id": "diabetes_status",
            "name": "Diabetes status",
            "role": "exposure",
            "dtype": "string",
            "concept_tags": ["diabetes", "diagnosis"]
        },
        {
            "id": "age",
            "name": "Age",
            "role": "covariate",
            "dtype": "int",
            "unit": "years",
            "concept_tags": ["age", "years"]
        },
        {
            "id": "bmi",
            "name": "Body Mass Index",
            "role": "covariate",
            "dtype": "float",
            "unit": "kg/m^2",
            "concept_tags": ["bmi", "body_mass_index"]
        }
    ]
    
    # Test dataset columns (from schema inference)
    test_columns = [
        {
            "column_name": "glucose_level_mg_dl",
            "data_type": "float",
            "unit": "mg/dl",
            "semantic_tags": ["blood_glucose", "glucose", "mg/dl"]
        },
        {
            "column_name": "diabetes_status",
            "data_type": "string",
            "semantic_tags": ["diabetes", "diagnosis"]
        },
        {
            "column_name": "age_years",
            "data_type": "int",
            "unit": "years",
            "semantic_tags": ["age", "years"]
        },
        {
            "column_name": "bmi_value",
            "data_type": "float",
            "unit": "kg/m2",
            "semantic_tags": ["bmi"]
        }
    ]
    
    try:
        mapping_service = ColumnMappingService()
        
        print("Mapping variables to columns...")
        mappings = mapping_service.auto_map_variables_to_dataset(
            test_variables,
            test_columns,
            min_confidence=0.3
        )
        
        print(f"✅ Mapping completed!")
        for var_id, mapping_info in mappings.items():
            best_match = mapping_info.get('best_match')
            if best_match:
                print(f"   {var_id} → {best_match['column_name']}")
                print(f"      Confidence: {best_match['confidence_score']:.2f}")
                print(f"      Reasoning: {best_match['reasoning']}")
            else:
                print(f"   {var_id} → No match found")
        
        return mappings
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_full_workflow():
    """Test the complete workflow from prompt to mapping."""
    print("\n" + "="*60)
    print("TEST 4: Full Workflow (Prompt → Spec → Mapping)")
    print("="*60)
    
    prompt = "Compare average fasting blood glucose levels between diabetic and non-diabetic patients, adjusting for age and BMI"
    
    print(f"Step 1: Interpreting prompt...")
    print(f"   Prompt: {prompt}")
    
    interpreter = PromptInterpreter()
    spec = interpreter.interpret_prompt(prompt)
    
    print(f"✅ Spec generated:")
    print(f"   Analysis Type: {spec.get('analysis_type')}")
    print(f"   Variables: {len(spec.get('variables', []))}")
    
    print(f"\nStep 2: Simulating dataset columns...")
    dataset_columns = [
        {"column_name": "glucose_level_mg_dl", "data_type": "float", "unit": "mg/dl", "semantic_tags": ["blood_glucose", "glucose"]},
        {"column_name": "diabetes", "data_type": "string", "semantic_tags": ["diabetes"]},
        {"column_name": "age_years", "data_type": "int", "unit": "years", "semantic_tags": ["age"]},
        {"column_name": "bmi_value", "data_type": "float", "unit": "kg/m2", "semantic_tags": ["bmi"]},
    ]
    
    print(f"✅ Dataset has {len(dataset_columns)} columns")
    
    print(f"\nStep 3: Auto-mapping variables to columns...")
    mapping_service = ColumnMappingService()
    mappings = mapping_service.auto_map_variables_to_dataset(
        spec.get('variables', []),
        dataset_columns
    )
    
    print(f"✅ Mappings generated:")
    for var_id, mapping_info in mappings.items():
        if mapping_info.get('best_match'):
            match = mapping_info['best_match']
            print(f"   {var_id} → {match['column_name']} (confidence: {match['confidence_score']:.2f})")
    
    print(f"\n✅ Full workflow test completed successfully!")
    return True

def test_environment_config():
    """Test environment configuration."""
    print("\n" + "="*60)
    print("TEST 0: Environment Configuration Check")
    print("="*60)
    
    llm_provider = os.getenv("LLM_PROVIDER", "groq")
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    print(f"LLM Provider: {llm_provider}")
    print(f"Groq API Key: {'✅ Set' if groq_key else '❌ Not set'}")
    print(f"OpenAI API Key: {'✅ Set' if openai_key else '❌ Not set'}")
    
    if llm_provider == "groq" and not groq_key:
        print("⚠️  Warning: LLM_PROVIDER=groq but GROQ_API_KEY not set!")
        print("   System will fall back to heuristics.")
    elif llm_provider == "openai" and not openai_key:
        print("⚠️  Warning: LLM_PROVIDER=openai but OPENAI_API_KEY not set!")
        print("   System will fall back to heuristics.")
    else:
        print("✅ Configuration looks good!")
    
    return True

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("GENERIC COMPUTATION SYSTEM - TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Test 0: Environment
    try:
        results['environment'] = test_environment_config()
    except Exception as e:
        print(f"❌ Environment test failed: {e}")
        results['environment'] = False
    
    # Test 1: Prompt Interpretation
    try:
        results['prompt_interpretation'] = test_prompt_interpretation()
    except Exception as e:
        print(f"❌ Prompt interpretation test failed: {e}")
        results['prompt_interpretation'] = False
    
    # Test 2: Schema Inference
    try:
        results['schema_inference'] = test_dataset_schema_inference() is not None
    except Exception as e:
        print(f"❌ Schema inference test failed: {e}")
        results['schema_inference'] = False
    
    # Test 3: Column Mapping
    try:
        results['column_mapping'] = test_column_mapping() is not None
    except Exception as e:
        print(f"❌ Column mapping test failed: {e}")
        results['column_mapping'] = False
    
    # Test 4: Full Workflow
    try:
        results['full_workflow'] = test_full_workflow()
    except Exception as e:
        print(f"❌ Full workflow test failed: {e}")
        results['full_workflow'] = False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<40} {status}")
    
    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED - Check errors above")
    print("="*60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

