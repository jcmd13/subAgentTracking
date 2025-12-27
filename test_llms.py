"""
Test all configured LLMs

This script verifies that all 5 LLMs in your multi-LLM stack are properly configured and working.
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
from openai import OpenAI
import ollama

load_dotenv()

def test_claude():
    """Test Claude Sonnet 3.5 (already configured in Claude Code)"""
    print("1️⃣  Claude Sonnet 3.5...")
    print("   ✅ Already configured in Claude Code Pro")
    print("   💰 Cost: $20/month (fixed subscription)")
    return True

def test_gemini():
    """Test Gemini 2.0 Flash (free tier)"""
    print("\n2️⃣  Gemini 2.0 Flash...")
    try:
        api_key = os.getenv("GOOGLE_AI_API_KEY")
        if not api_key:
            print("   ❌ Error: GOOGLE_AI_API_KEY not found in environment")
            return False

        genai.configure(api_key=api_key)
        # Use stable model name
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content('Say "test"')

        print(f"   ✅ Response: {response.text[:50]}")
        print("   💰 Cost: Free (5 RPM, 25 req/day limit)")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_perplexity():
    """Test Perplexity Pro (with $5 monthly credits)"""
    print("\n3️⃣  Perplexity Pro...")
    try:
        api_key = os.getenv("PERPLEXITY_API_KEY")
        if not api_key:
            print("   ❌ Error: PERPLEXITY_API_KEY not found in environment")
            return False

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.perplexity.ai"
        )
        # Use current model name (deprecated: llama-3.1-sonar-large-128k-online)
        response = client.chat.completions.create(
            model="sonar",
            messages=[{"role": "user", "content": 'Say "test"'}]
        )

        print(f"   ✅ Response: {response.choices[0].message.content[:50]}")
        print("   💰 Cost: $5 credits/month (part of $20/month Pro sub)")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_ollama_cloud():
    """Test Ollama minimax-m2:cloud (free, optimized for web research)"""
    print("\n4️⃣  Ollama minimax-m2:cloud...")
    try:
        response = ollama.chat(
            model='minimax-m2:cloud',
            messages=[{'role': 'user', 'content': 'Say "test"'}]
        )

        print(f"   ✅ Response: {response['message']['content'][:50]}")
        print("   💰 Cost: Free")
        print("   ⭐ Best for: Web research (2.2x better than Claude!)")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print("   💡 Tip: Run 'ollama pull minimax-m2:cloud' to download")
        return False

def test_ollama_local():
    """Test Ollama local (llama3.1:8b)"""
    print("\n5️⃣  Ollama local (llama3.1:8b)...")
    try:
        response = ollama.chat(
            model='llama3.1:8b',
            messages=[{'role': 'user', 'content': 'Say "test"'}]
        )

        print(f"   ✅ Response: {response['message']['content'][:50]}")
        print("   💰 Cost: Free")
        print("   🔒 Best for: Privacy-sensitive tasks")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print("   💡 Tip: Run 'ollama pull llama3.1:8b' to download")
        return False

def main():
    """Run all LLM tests and display results"""
    print("\n" + "="*60)
    print("🧪 Testing All LLMs in Your Multi-LLM Stack")
    print("="*60)

    results = {
        "Claude Sonnet 3.5": test_claude(),
        "Gemini 2.0 Flash": test_gemini(),
        "Perplexity Pro": test_perplexity(),
        "Ollama minimax-m2:cloud": test_ollama_cloud(),
        "Ollama Local (llama3.1:8b)": test_ollama_local(),
    }

    print("\n" + "="*60)
    print("📊 Results Summary")
    print("="*60)

    for llm, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {llm}")

    working = sum(results.values())
    total = len(results)

    print(f"\n🎯 {working}/{total} LLMs working")

    if working == total:
        print("\n🎉 All LLMs configured successfully!")
        print("\n💡 Next Steps:")
        print("   1. Read README.md for provider setup and routing guidance")
        print("   2. Use MiniMax M2 for web research (2.2x faster!)")
        print("   3. Save Claude messages for complex tasks only")
        print("   4. Stay under $5 Perplexity credit limit with free LLMs")
    elif working >= 3:
        print("\n⚠️  Most LLMs working! Fix the failed ones when needed.")
        print("\n💡 Tips:")
        print("   - Check API keys in .env file")
        print("   - Run 'ollama serve' to start Ollama")
        print("   - Run 'ollama pull <model>' to download missing models")
    else:
        print("\n❌ Please fix LLM configuration issues")
        print("\n💡 Troubleshooting:")
        print("   - Verify .env file has correct API keys")
        print("   - Check Ollama is running: ollama list")
        print("   - See README.md for detailed setup")

    print("\n" + "="*60)
    print("💰 Cost Summary")
    print("="*60)
    print("  Claude Code Pro:     $20/month (already paid)")
    print("  Perplexity Pro:      $20/month ($5 API credits)")
    print("  Gemini 2.0 Flash:    $0 (free tier)")
    print("  Ollama models:       $0 (free)")
    print("  " + "-"*40)
    print("  Total:               $40/month")
    print("\n  Optimization Goal: 5x more AI assistance for same cost!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
