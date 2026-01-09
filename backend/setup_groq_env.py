"""
Script to add Groq configuration to .env file
"""

from pathlib import Path

# Find project root
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"

print(f"Updating .env file at: {env_path}\n")

# Groq configuration to add
groq_config = """
# LLM / Prompt Interpretation Configuration - Groq (FREE)
LLM_PROVIDER=groq
GROQ_API_KEY=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
GROQ_MODEL=llama-3.1-8b-instant
LLM_TIMEOUT_SECONDS=15
"""

if env_path.exists():
    # Read existing content
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if Groq config already exists
    if 'GROQ_API_KEY' in content:
        print("⚠️  GROQ_API_KEY already exists in .env")
        print("   Please check the file manually or remove the old entry first.")
        response = input("   Do you want to replace it? (y/n): ")
        if response.lower() != 'y':
            print("   Cancelled.")
            exit(0)
        # Remove old Groq config
        lines = content.split('\n')
        new_lines = []
        skip_until = None
        for i, line in enumerate(lines):
            if 'GROQ' in line.upper() or 'LLM_PROVIDER' in line.upper():
                if skip_until is None:
                    skip_until = i
                continue
            elif skip_until is not None and line.strip() and not line.strip().startswith('#'):
                # Check if we've moved past the LLM section
                if any(x in line.upper() for x in ['MONITORING', 'FRONTEND', 'AUDIT', 'NEXT_PUBLIC']):
                    skip_until = None
                    new_lines.append(line)
                elif skip_until is not None:
                    continue
                else:
                    new_lines.append(line)
            else:
                if skip_until is None:
                    new_lines.append(line)
        
        content = '\n'.join(new_lines)
    
    # Append Groq config
    if not content.endswith('\n'):
        content += '\n'
    content += groq_config
    
    # Write back
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Successfully added Groq configuration to .env file!")
    print("\nAdded:")
    print("  - LLM_PROVIDER=groq")
    print("  - GROQ_API_KEY=...")
    print("  - GROQ_MODEL=llama-3.1-8b-instant")
    print("\nNow run: python test_groq_integration.py")
    
else:
    print(f"❌ .env file not found at {env_path}")
    print("   Please create it first from env.template")

