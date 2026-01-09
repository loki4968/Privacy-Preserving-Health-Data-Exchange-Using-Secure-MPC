# ✅ Groq API Key Configuration

Your Groq API key has been received! Here's how to set it up:

## Step 1: Update your .env file

Add these lines to your `.env` file in the project root:

```bash
# LLM Provider - Use Groq (FREE, 14,400 requests/day)
LLM_PROVIDER=groq
GROQ_API_KEY=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
GROQ_MODEL=llama-3.1-8b-instant
LLM_TIMEOUT_SECONDS=15
```

## Step 2: Restart your backend

After updating `.env`, restart your backend server:

```bash
# If running with uvicorn
cd backend
uvicorn main:app --reload
```

## Step 3: Test it!

Try creating a computation with a natural language prompt:

**Example prompt:**
> "Compare average fasting blood glucose levels between diabetic and non-diabetic patients, adjusting for age and BMI over the last 6 months"

The system will now use Groq to interpret your prompt automatically! 🎉

## What you get:

- ✅ **14,400 free requests per day** (plenty for most use cases)
- ✅ **Fast inference** (usually < 1 second)
- ✅ **Good quality** prompt interpretation
- ✅ **No cost** - completely free!

## Security Note:

Your `.env` file is already in `.gitignore`, so your API key won't be committed to git. Keep it safe and don't share it publicly!

## Troubleshooting:

If you see errors:
1. Make sure the API key is correct (starts with `gsk_`)
2. Check that `LLM_PROVIDER=groq` is set
3. Restart the backend after changing `.env`
4. Check backend logs for specific error messages

Enjoy your free AI-powered prompt interpretation! 🚀

