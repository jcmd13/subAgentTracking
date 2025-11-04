# Multi-LLM Setup Guide

**Quick setup guide for all 5 LLMs in your cost-optimized stack**

**Time**: 15 minutes total

---

## Overview

You'll set up:
1. ✅ **Claude Sonnet 3.5** - Already configured (Claude Code Pro subscription)
2. ⏳ **Gemini 2.0 Flash** - 5 minutes (free tier: 5 RPM, 25 req/day)
3. ⏳ **Perplexity Pro** - 3 minutes ($5 monthly API credits with Pro sub)
4. ⏳ **Ollama minimax-m2:cloud** - 2 minutes (pull model)
5. ⏳ **Ollama local models** - 5 minutes (pull models)

---

## 1. Claude Sonnet 3.5 ✅

**Status**: Already configured in Claude Code

**Your Current Setup**:
- Claude Code Pro subscription: $20/month
- Message limits: ~45 messages per 5-hour window
- Shared usage pool between Claude Code and web chat
- NOT pay-per-token API billing

**No additional setup needed!**

---

## 2. Gemini 2.0 Flash (5 Minutes)

### Step 1: Get API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Get API key"
4. Click "Create API key in new project"
5. Copy the API key (starts with `AIza...`)

**Note**: Free tier provides 5 RPM (requests per minute) and 25 requests/day. No subscription required.

### Step 2: Save API Key

```bash
# Navigate to project
cd /Users/john/Personal-Projects/subAgentTracking

# Create .env file (if not exists)
touch .env

# Add API key
echo "GOOGLE_AI_API_KEY=your_api_key_here" >> .env

# Verify
cat .env | grep GOOGLE_AI_API_KEY
```

### Step 3: Install Python SDK

```bash
# Activate virtual environment
source venv/bin/activate

# Install Google AI SDK
pip install google-generativeai

# Verify installation
python -c "import google.generativeai as genai; print('✅ Gemini SDK installed')"
```

### Step 4: Test Connection

```bash
python -c "
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_AI_API_KEY'))

# Use stable model name
model = genai.GenerativeModel('gemini-2.0-flash')
response = model.generate_content('Say hello!')

print('✅ Gemini 2.0 Flash working!')
print(f'Response: {response.text}')
"
```

**Expected output**:
```
✅ Gemini 2.0 Flash working!
Response: Hello! How can I help you today?
```

**Available Models**:
- `gemini-2.0-flash` - Fast, efficient (recommended)
- `gemini-2.5-flash` - Latest stable Flash variant
- `gemini-2.5-pro` - Most capable (requires paid tier for production)

**Troubleshooting**:
- **"API key not valid"**: Check you're using the API key from [AI Studio](https://aistudio.google.com/app/apikey), not Google Cloud API key
- **"Quota exceeded"**: Free tier has 5 RPM and 25 requests/day limit. Upgrade to paid tier or reduce frequency
- **"Model not found"**: Use stable model names above. Avoid experimental model names

---

## 3. Perplexity Pro (3 Minutes)

### Step 1: Get API Key

1. Go to [Perplexity Settings](https://www.perplexity.ai/settings/api)
2. Sign in with your Pro account
3. Set up billing information (required even for credits)
4. Click "Generate API Key"
5. Copy the API key (starts with `pplx-...`)

**Note**: Pro subscription ($20/month) includes $5 monthly API credits. You must add billing info but won't be charged unless you exceed $5/month.

### Step 2: Save API Key

```bash
# Add to .env file
echo "PERPLEXITY_API_KEY=your_api_key_here" >> .env

# Verify
cat .env | grep PERPLEXITY_API_KEY
```

### Step 3: Install SDK

```bash
# Perplexity uses OpenAI-compatible API
pip install openai

# Verify
python -c "from openai import OpenAI; print('✅ OpenAI SDK installed')"
```

### Step 4: Test Connection

```bash
python -c "
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv('PERPLEXITY_API_KEY'),
    base_url='https://api.perplexity.ai'
)

# Use current model name
response = client.chat.completions.create(
    model='sonar',
    messages=[
        {'role': 'user', 'content': 'What is the latest version of Python?'}
    ]
)

print('✅ Perplexity Pro working!')
print(f'Response: {response.choices[0].message.content}')
"
```

**Expected output**:
```
✅ Perplexity Pro working!
Response: As of [current date], the latest stable version of Python is 3.12.x...
```

**Available Models**:
- `sonar` - Fast search model (recommended)
- `sonar-pro` - More capable search
- `sonar-reasoning` - Multi-step reasoning
- `sonar-reasoning-pro` - Advanced reasoning

**Troubleshooting**:
- **"Billing required"**: Add payment method in settings even though you have $5 credits (won't be charged unless you exceed $5/month)
- **"Invalid API key"**: Regenerate key in settings. Make sure no extra spaces in .env file
- **"Model not found"**: Use current model names above. Old llama-3.1-sonar models were deprecated in February 2025
- **"Rate limit exceeded"**: Wait and try again, or check your usage

---

## 4. Ollama minimax-m2:cloud (2 Minutes)

### Step 1: Verify Ollama Installed

```bash
# Check Ollama is running
ollama list

# If not running:
ollama serve
```

### Step 2: Pull Cloud Model

```bash
# Pull minimax-m2:cloud (released October 28, 2025)
ollama pull minimax-m2:cloud

# This may take 2-3 minutes depending on connection
```

**Expected output**:
```
pulling manifest
pulling ff6fc1c1d...
pulling 78a6f3e67...
pulling 1e71c90ef...
verifying sha256 digest
writing manifest
success
```

### Step 3: Verify Model

```bash
# List models
ollama list | grep minimax

# Should show:
# minimax-m2:cloud    [size]    [date]
```

### Step 4: Test Model

```bash
# Test with simple prompt
ollama run minimax-m2:cloud "Say hello in JSON format"

# Expected output (JSON):
# {"message": "Hello!", "status": "success"}
```

**Troubleshooting**:
- **"Model not found"**: Check exact model name (`minimax-m2:cloud`)
- **"Connection error"**: Ensure `ollama serve` is running
- **"Download failed"**: Check internet connection, try again

---

## 5. Ollama Local Models (5 Minutes)

### Step 1: Pull Recommended Local Models

```bash
# Fast general-purpose model (4.7 GB)
ollama pull llama3.1:8b

# Code-focused model (3.8 GB)
ollama pull codellama:7b

# Lightweight model (4.1 GB)
ollama pull mistral:7b

# Code generation specialist (3.8 GB)
ollama pull deepseek-coder:6.7b
```

**Note**: Each model takes 2-5 minutes to download depending on connection

### Step 2: Verify All Models

```bash
ollama list
```

**Expected output**:
```
NAME                    SIZE    MODIFIED
minimax-m2:cloud        [size]  [date]
llama3.1:8b            4.7 GB  [date]
codellama:7b           3.8 GB  [date]
mistral:7b             4.1 GB  [date]
deepseek-coder:6.7b    3.8 GB  [date]
```

### Step 3: Test Local Models

```bash
# Test llama3.1:8b
ollama run llama3.1:8b "Write a Python function to reverse a string"

# Test codellama:7b
ollama run codellama:7b "// Function to calculate fibonacci"

# Test mistral:7b
ollama run mistral:7b "Explain async/await in Python"

# Test deepseek-coder:6.7b
ollama run deepseek-coder:6.7b "def quicksort(arr):"
```

---

## Verification: Test All LLMs

Create a test script to verify all LLMs are working:

**File**: `test_llms.py`

```python
"""
Test all configured LLMs
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
from openai import OpenAI
import ollama

load_dotenv()

def test_claude():
    print("1️⃣  Claude Sonnet 3.5...")
    print("   ✅ Already configured in Claude Code")
    return True

def test_gemini():
    print("2️⃣  Gemini 2.0 Flash...")
    try:
        genai.configure(api_key=os.getenv("GOOGLE_AI_API_KEY"))
        # Use stable model name
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content('Say "test"')
        print(f"   ✅ Response: {response.text[:50]}")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_perplexity():
    print("3️⃣  Perplexity Pro...")
    try:
        client = OpenAI(
            api_key=os.getenv("PERPLEXITY_API_KEY"),
            base_url="https://api.perplexity.ai"
        )
        # Use current model name
        response = client.chat.completions.create(
            model="sonar",
            messages=[{"role": "user", "content": 'Say "test"'}]
        )
        print(f"   ✅ Response: {response.choices[0].message.content[:50]}")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_ollama_cloud():
    print("4️⃣  Ollama minimax-m2:cloud...")
    try:
        response = ollama.chat(
            model='minimax-m2:cloud',
            messages=[{'role': 'user', 'content': 'Say "test"'}]
        )
        print(f"   ✅ Response: {response['message']['content'][:50]}")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_ollama_local():
    print("5️⃣  Ollama local (llama3.1:8b)...")
    try:
        response = ollama.chat(
            model='llama3.1:8b',
            messages=[{'role': 'user', 'content': 'Say "test"'}]
        )
        print(f"   ✅ Response: {response['message']['content'][:50]}")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("\n🧪 Testing All LLMs\n")

    results = {
        "Claude Sonnet 3.5": test_claude(),
        "Gemini 2.0 Flash": test_gemini(),
        "Perplexity Pro": test_perplexity(),
        "Ollama Cloud": test_ollama_cloud(),
        "Ollama Local": test_ollama_local(),
    }

    print("\n📊 Results:")
    for llm, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {llm}")

    working = sum(results.values())
    total = len(results)
    print(f"\n🎯 {working}/{total} LLMs working")

    if working == total:
        print("\n🎉 All LLMs configured successfully!")
    elif working >= 3:
        print("\n⚠️  Most LLMs working, fix the failed ones when needed")
    else:
        print("\n❌ Please fix LLM configuration issues")
```

### Run Test Script

```bash
python test_llms.py
```

**Expected output**:
```
🧪 Testing All LLMs

1️⃣  Claude Sonnet 3.5...
   ✅ Already configured in Claude Code
2️⃣  Gemini 2.0 Flash...
   ✅ Response: Test
3️⃣  Perplexity Pro...
   ✅ Response: Test
4️⃣  Ollama minimax-m2:cloud...
   ✅ Response: test
5️⃣  Ollama local (llama3.1:8b)...
   ✅ Response: Test!

📊 Results:
  ✅ Claude Sonnet 3.5
  ✅ Gemini 2.0 Flash
  ✅ Perplexity Pro
  ✅ Ollama Cloud
  ✅ Ollama Local

🎯 5/5 LLMs working

🎉 All LLMs configured successfully!
```

---

## Environment Variables Summary

Your `.env` file should contain:

```bash
# Google Gemini API (free tier: 5 RPM, 25 req/day)
GOOGLE_AI_API_KEY=AIza...your_key_here

# Perplexity API ($5 monthly credits with Pro sub)
PERPLEXITY_API_KEY=pplx-...your_key_here

# Google Drive API (if configured later)
# Stored in .claude/credentials/google_drive_credentials.json
# Stored in .claude/credentials/google_drive_token.json
```

---

## Cost Summary

| LLM | Monthly Cost | Notes |
|-----|--------------|-------|
| Claude Sonnet 3.5 | $20 (fixed) | Claude Code Pro subscription (already paid) |
| Gemini 2.0 Flash | $0 | Free tier: 5 RPM, 25 req/day |
| Perplexity Pro | $20 ($5 credits) | $20/month subscription includes $5 API credits |
| Ollama minimax-m2:cloud | $0 | Free cloud model |
| Ollama local | $0 | Free, runs on your Mac |

**Total**: $40/month (Claude Code Pro + Perplexity Pro subscriptions)

**Optimization Goal**: Use free Gemini/Ollama to stay under $5/month Perplexity credit limit

---

## Usage Examples

### Example 1: Use Gemini for Test Generation

```python
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_AI_API_KEY"))

# Use stable model name
model = genai.GenerativeModel('gemini-2.0-flash')

prompt = """
Generate pytest unit tests for this function:

def parse_log(log_line: str) -> dict:
    parts = log_line.split('|')
    return {
        'timestamp': parts[0],
        'level': parts[1],
        'message': parts[2]
    }
"""

response = model.generate_content(prompt)
print(response.text)
```

---

### Example 2: Use Perplexity for Research

```python
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai"
)

# Use current model name
response = client.chat.completions.create(
    model="sonar",
    messages=[{
        "role": "user",
        "content": "What are the latest Python async best practices in 2025?"
    }]
)

print(response.choices[0].message.content)
```

---

### Example 3: Use Ollama Cloud for Simple Tasks

```python
import ollama

# Parse JSON log
response = ollama.chat(
    model='minimax-m2:cloud',
    messages=[{
        'role': 'user',
        'content': 'Parse this JSON and extract error messages: {...}'
    }]
)

print(response['message']['content'])
```

---

### Example 4: Use Ollama Local for Sensitive Data

```python
import ollama

# Redact sensitive data (stays on your machine)
response = ollama.chat(
    model='llama3.1:8b',
    messages=[{
        'role': 'user',
        'content': 'Redact API keys and passwords from this log: {...}'
    }]
)

print(response['message']['content'])
```

---

## Next Steps

1. ✅ All LLMs configured
2. ⏳ Read [MULTI_LLM_ARCHITECTURE.md](MULTI_LLM_ARCHITECTURE.md)
3. ⏳ Implement LLM router (`src/core/llm_router.py`)
4. ⏳ Update agent system with multi-LLM support
5. ⏳ Start optimizing costs with targeted model selection! 🎉

---

**Setup complete!** You now have a 5-LLM stack for cost-optimized development.

**Key Takeaways**:
- Gemini 2.0 Flash: Free tier (5 RPM, 25 req/day)
- Perplexity: $20/month sub includes $5 monthly API credits
- Claude Code: $20/month Pro subscription (already paid)
- Ollama: Free local and cloud models
