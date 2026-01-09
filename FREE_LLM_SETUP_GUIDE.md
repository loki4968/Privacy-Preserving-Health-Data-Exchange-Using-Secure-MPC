# Free LLM Setup Guide for Prompt Interpretation

The system supports multiple **FREE** LLM providers for prompt interpretation. No need to pay for OpenAI!

## 🆓 Free Options (Recommended)

### 1. **Groq** (Recommended - Default Provider)
- ✅ **FREE tier: 14,400 requests/day**
- ✅ Very fast inference
- ✅ Good quality results
- ✅ Easy setup
- ✅ **Default provider** - no configuration needed if API key is set

**Setup Steps:**
1. Sign up at https://console.groq.com (free)
2. Get your API key from the dashboard
3. Add to `.env`:

```bash
LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL=llama-3.1-8b-instant  # Fast and free
```

**Models Available:**
- `llama-3.1-8b-instant` (recommended, fastest)
- `llama-3.1-70b-versatile` (better quality, slower)
- `mixtral-8x7b-32768` (good balance)

### 3. **Ollama** (Local, Completely Free)
- ✅ **100% FREE** - Runs locally on your machine
- ✅ No API limits
- ✅ No internet required after setup
- ✅ Privacy-friendly (data never leaves your machine)
- ⚠️ Requires local installation

**Setup Steps:**
1. Install Ollama from https://ollama.ai
2. Pull a model:
   ```bash
   ollama pull llama3.2
   # or
   ollama pull mistral
   ```
3. Add to `.env`:

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

**Recommended Models:**
- `llama3.2` - Good balance of speed and quality
- `mistral` - Fast and efficient
- `llama3` - Better quality, slower

### 4. **Hugging Face Inference API** (Free Tier)
- ✅ **FREE tier: 1,000 requests/month**
- ✅ Good for testing
- ⚠️ Limited requests

**Setup Steps:**
1. Sign up at https://huggingface.co
2. Get API token from https://huggingface.co/settings/tokens
3. Add to `.env`:

```bash
LLM_PROVIDER=huggingface
HUGGINGFACE_API_KEY=your-hf-token-here
HF_MODEL=mistralai/Mistral-7B-Instruct-v0.2
```

**Free Models Available:**
- `mistralai/Mistral-7B-Instruct-v0.2`
- `meta-llama/Llama-2-7b-chat-hf` (requires request access)
- `google/flan-t5-large` (smaller, faster)

## 💰 Paid Option (Optional)

### 5. **OpenAI** (Paid)
- ⚠️ Requires paid API key
- ✅ Best quality results
- ✅ Most reliable

**Setup:**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-key-here
OPENAI_MODEL=gpt-4o-mini  # Cheapest option
```

## 🚀 Quick Start (Recommended)

**Groq is now the default provider!** For the easiest setup with good results:

1. Sign up at https://console.groq.com (takes 2 minutes)
2. Copy your API key
3. Add to `.env`:

```bash
LLM_PROVIDER=groq  # This is now the default, but explicit is good
GROQ_API_KEY=your-key-here
```

That's it! You get 14,400 free requests per day. If you don't set `GROQ_API_KEY`, the system will automatically fall back to enhanced heuristics (no setup required).

## 📊 Comparison

| Provider | Cost | Speed | Quality | Setup Difficulty |
|----------|------|-------|---------|------------------|
| **Heuristics** | FREE | ⚡⚡⚡ | ⭐⭐ | ✅ None |
| **Groq** | FREE | ⚡⚡⚡ | ⭐⭐⭐⭐ | ✅ Easy |
| **Ollama** | FREE | ⚡⚡ | ⭐⭐⭐⭐ | ⚠️ Medium |
| **Hugging Face** | FREE* | ⚡⚡ | ⭐⭐⭐ | ✅ Easy |
| **OpenAI** | 💰 Paid | ⚡⚡ | ⭐⭐⭐⭐⭐ | ✅ Easy |

*1,000 requests/month free

## 🔄 Fallback Behavior

The system automatically falls back through providers:
1. Tries your configured provider
2. If that fails, tries Groq (if API key set)
3. If that fails, tries Ollama (if running)
4. Finally falls back to enhanced heuristics (always works)

So even if your primary provider fails, the system keeps working!

## 🎯 Recommendation

**For most users:** Use **Groq** - it's free, fast, and easy to set up.

**For privacy-conscious users:** Use **Ollama** - runs locally, no data leaves your machine.

**For testing/development:** Use **heuristics** - no setup needed, always works.

## 📝 Example .env Configuration

```bash
# Recommended: Groq (free, fast, good quality)
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here
GROQ_MODEL=llama-3.1-8b-instant

# Or use heuristics (no API key needed)
# LLM_PROVIDER=heuristic

# Or use Ollama (local, private)
# LLM_PROVIDER=ollama
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama3.2
```

## ❓ Troubleshooting

### Groq not working?
- Check your API key is correct
- Verify you're within the 14,400/day limit
- Try a different model

### Ollama not working?
- Make sure Ollama is running: `ollama serve`
- Verify the model is installed: `ollama list`
- Check the base URL matches your Ollama installation

### Hugging Face not working?
- Check your API token is valid
- Verify you're within the 1,000/month limit
- Some models require request access first

### All LLMs failing?
- System automatically falls back to heuristics
- Check logs for specific error messages
- Heuristics will always work as a fallback

## 🎉 No Cost Required!

You can use the system completely free with:
- Enhanced heuristics (default)
- Groq free tier
- Ollama local
- Hugging Face free tier

No need to pay for OpenAI unless you want the absolute best quality!

