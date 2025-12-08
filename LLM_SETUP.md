# 🤖 Multi-LLM Setup Guide

The Research Agent supports multiple LLM providers. You can use whichever one you have access to!

## 🎯 Supported Providers

| Provider | Cost | Setup Difficulty | Best For |
|----------|------|------------------|----------|
| **Claude** (Anthropic) | Pay-per-use | Easy | Best quality, reasoning |
| **Gemini** (Google) | Free tier available | Easy | Cost-effective, multimodal |
| **OpenAI** (GPT-4) | Pay-per-use | Easy | General purpose |
| **Ollama** (Local) | Free | Medium | Privacy, no API costs |

## 🚀 Quick Start

### 1. Check What You Have

```bash
python check_llms.py
```

This shows:
- ✅ Which LLMs are configured
- ❌ Which are missing
- 🔧 Which one is currently active

### 2. Configure Your Preferred LLM

Edit `.env` file:

```bash
# Choose your provider
LLM_PROVIDER=claude  # Options: claude, gemini, openai, ollama

# Add your API keys (only need the ones you want to use)
ANTHROPIC_API_KEY=sk-ant-your-key
GEMINI_API_KEY=your-key
OPENAI_API_KEY=sk-your-key
```

### 3. Test It

```bash
python check_llms.py
```

## 📝 Provider-Specific Setup

### Claude (Anthropic)

**Get API Key:**
1. Go to https://console.anthropic.com/settings/keys
2. Click "Create Key"
3. Copy the key

**Add to .env:**
```bash
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Pricing:** ~$3 per million input tokens, $15 per million output tokens

---

### Gemini (Google)

**Get API Key:**
1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key

**Add to .env:**
```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIzaSy...
```

**Pricing:** Free tier: 60 requests/minute. Paid: $0.50 per million tokens

---

### OpenAI (GPT-4)

**Get API Key:**
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key

**Add to .env:**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
```

**Pricing:** GPT-4 Turbo: ~$10 per million input tokens, $30 per million output tokens

---

### Ollama (Local - FREE!)

**Install Ollama:**

**Mac/Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download from https://ollama.ai/download

**Setup:**
```bash
# Pull a model (llama2, mistral, mixtral, etc.)
ollama pull llama2

# Start Ollama server
ollama serve
```

**Add to .env:**
```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama2
OLLAMA_BASE_URL=http://localhost:11434
```

**Pros:**
- 100% Free
- No API limits
- Privacy (runs locally)

**Cons:**
- Requires good GPU/CPU
- Slower than cloud APIs
- Quality depends on model size

---

## 🔄 Switching Between Providers

Just change `LLM_PROVIDER` in `.env`:

```bash
# Use Claude
LLM_PROVIDER=claude

# Use Gemini
LLM_PROVIDER=gemini

# Use OpenAI
LLM_PROVIDER=openai

# Use local Ollama
LLM_PROVIDER=ollama
```

No code changes needed! 🎉

## 💡 Recommendations

**For Testing:**
- Use **Gemini** (free tier) or **Ollama** (free, local)

**For Production:**
- Use **Claude** (best quality) or **GPT-4** (reliable)

**For Cost Optimization:**
- Use **Gemini** (cheapest cloud option)
- Use **Ollama** (free but needs hardware)

**For Privacy:**
- Use **Ollama** (everything stays local)

## 🧪 Testing Different Providers

You can test each provider individually:

```python
from src.llm_provider import LLMFactory

# Test Claude
claude = LLMFactory.create_provider("claude")
print(claude.generate("Hello!"))

# Test Gemini
gemini = LLMFactory.create_provider("gemini")
print(gemini.generate("Hello!"))

# Test OpenAI
openai = LLMFactory.create_provider("openai")
print(openai.generate("Hello!"))

# Test Ollama
ollama = LLMFactory.create_provider("ollama")
print(ollama.generate("Hello!"))
```

## 🐛 Troubleshooting

**"No LLM configured" error:**
- Add at least one API key to `.env`
- Or install and run Ollama

**"API key invalid" error:**
- Check your API key is correct
- Verify you have credits/billing enabled
- Make sure key has necessary permissions

**"Ollama connection refused" error:**
- Run `ollama serve` in another terminal
- Check Ollama is running: `curl http://localhost:11434`

**"Rate limit exceeded" error:**
- Switch to a different provider
- Wait a few minutes
- Upgrade your API plan

## 📊 Cost Comparison (for 1M tokens)

Typical research task: ~50,000 tokens (input + output)

| Provider | Cost per Research |
|----------|-------------------|
| Gemini | ~$0.03 |
| Claude | ~$0.15 |
| GPT-4 | ~$0.20 |
| Ollama | $0.00 (free) |

## 🎯 Best Practice

1. **Start with Gemini or Ollama** (free/cheap testing)
2. **Switch to Claude or GPT-4** when quality matters
3. **Use Ollama for high-volume** (if you have good hardware)
4. **Keep backup provider** configured in case one fails

## ❓ Questions?

Run these commands:
```bash
# Check current setup
python check_llms.py

# Test all configured providers
python test_setup.py

# Start research with current provider
python run_cli.py
```