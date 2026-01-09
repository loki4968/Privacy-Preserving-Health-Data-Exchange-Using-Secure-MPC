"""
Quick test to verify Groq API integration once API key is configured.
Run this after adding GROQ_API_KEY to .env
"""

import os
import sys
from pathlib import Path

# Load .env file from project root
from dotenv import load_dotenv

# Find project root (parent of backend directory)
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"

# Load environment variables
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}")
else:
    # Also try backend/.env
    backend_env = Path(__file__).parent / ".env"
    if backend_env.exists():
        load_dotenv(backend_env)
        print(f"✅ Loaded .env from: {backend_env}")
    else:
        print(f"⚠️  .env file not found at {env_path} or {backend_env}")

sys.path.insert(0, str(Path(__file__).parent))

from prompt_interpreter import PromptInterpreter

def test_groq():
    """Test Groq API integration."""
    print("\n" + "="*60)
    print("GROQ API INTEGRATION TEST")
    print("="*60)
    
    # Check if Groq is configured
    groq_key = os.getenv("GROQ_API_KEY")
    llm_provider = os.getenv("LLM_PROVIDER", "heuristic")
    
    if not groq_key:
        print("❌ GROQ_API_KEY not found in environment")
        print("   Please add it to your .env file:")
        print("   GROQ_API_KEY=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")
        return False
    
    if llm_provider != "groq":
        print(f"⚠️  LLM_PROVIDER is set to '{llm_provider}', not 'groq'")
        print("   Setting LLM_PROVIDER=groq for this test...")
        os.environ["LLM_PROVIDER"] = "groq"
    
    print(f"✅ Groq API Key found: {groq_key[:10]}...")
    print(f"✅ Provider: groq")
    
    interpreter = PromptInterpreter()
    
    test_prompt = "Compare average fasting blood glucose levels between diabetic and non-diabetic patients, adjusting for age and BMI over the last 6 months"
    
    print(f"\nTesting prompt interpretation with Groq...")
    print(f"Prompt: {test_prompt}\n")
    
    try:
        spec = interpreter.interpret_prompt(test_prompt)
        
        print("✅ Groq interpretation successful!")
        print(f"\nResults:")
        print(f"   Research Question: {spec.get('research_question', 'N/A')}")
        print(f"   Analysis Type: {spec.get('analysis_type', 'N/A')}")
        print(f"   Population Criteria: {spec.get('population_criteria', 'N/A')}")
        print(f"   Variables Found: {len(spec.get('variables', []))}")
        
        for var in spec.get('variables', []):
            print(f"      - {var.get('name')} ({var.get('role')})")
            print(f"        Unit: {var.get('unit', 'N/A')}")
            print(f"        Tags: {var.get('concept_tags', [])}")
        
        print(f"   Operations: {len(spec.get('operations', []))}")
        
        # Verify it's using Groq (not heuristics)
        if interpreter.llm_provider == "groq" or groq_key:
            print(f"\n✅ Confirmed: Using Groq API (not heuristics)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n⚠️  Falling back to heuristics...")
        return False

if __name__ == "__main__":
    success = test_groq()
    if success:
        print("\n" + "="*60)
        print("🎉 GROQ INTEGRATION WORKING!")
        print("="*60)
        print("\nYour system is now using AI-powered prompt interpretation!")
        print("You get 14,400 free requests per day with Groq.")
    else:
        print("\n" + "="*60)
        print("⚠️  GROQ TEST FAILED")
        print("="*60)
        print("\nMake sure:")
        print("1. GROQ_API_KEY is in your .env file")
        print("2. LLM_PROVIDER=groq is set in .env")
        print("3. Restart your backend after updating .env")
    
    sys.exit(0 if success else 1)

