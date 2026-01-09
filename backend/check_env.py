"""
Helper script to check and verify .env configuration
"""

from pathlib import Path
from dotenv import load_dotenv
import os

# Find project root
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"

print(f"Looking for .env at: {env_path}")
print(f"File exists: {env_path.exists()}\n")

if env_path.exists():
    # Load .env
    load_dotenv(env_path)
    
    print("="*60)
    print("ENVIRONMENT VARIABLES CHECK")
    print("="*60)
    
    # Check LLM variables
    llm_provider = os.getenv("LLM_PROVIDER")
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    print(f"\nLLM_PROVIDER: {llm_provider if llm_provider else 'NOT SET (defaults to heuristic)'}")
    print(f"GROQ_API_KEY: {'✅ SET' if groq_key else '❌ NOT SET'}")
    if groq_key:
        print(f"   Key preview: {groq_key[:15]}...")
    print(f"OPENAI_API_KEY: {'✅ SET' if openai_key else '❌ NOT SET'}")
    
    # Read raw .env content to check format
    print(f"\n" + "="*60)
    print("RAW .ENV CONTENT (LLM section):")
    print("="*60)
    
    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        in_llm_section = False
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            if 'LLM' in line_stripped.upper() or 'GROQ' in line_stripped.upper() or 'OPENAI' in line_stripped.upper():
                in_llm_section = True
                print(f"{i:3}: {line.rstrip()}")
            elif in_llm_section and line_stripped and not line_stripped.startswith('#'):
                # Check if we've moved to next section
                if any(x in line_stripped.upper() for x in ['MONITORING', 'FRONTEND', 'AUDIT']):
                    break
                if line_stripped and not line_stripped.startswith('#'):
                    print(f"{i:3}: {line.rstrip()}")
    
    # Provide fix instructions
    if not groq_key:
        print(f"\n" + "="*60)
        print("TO FIX: Add these lines to your .env file:")
        print("="*60)
        print("LLM_PROVIDER=groq")
        print("GROQ_API_KEY=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")
        print("GROQ_MODEL=llama-3.1-8b-instant")
else:
    print(f"❌ .env file not found at {env_path}")
    print(f"   Please create it from env.template")

