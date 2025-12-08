"""
Check which LLM providers are configured and available.
Run this to see what you can use!
"""
import os
from dotenv import load_dotenv
from src.llm_provider import LLMFactory

load_dotenv()

def main():
    print("╔═══════════════════════════════════════════════════╗")
    print("║   LLM Provider Status Check                       ║")
    print("╚═══════════════════════════════════════════════════╝")
    print()
    
    # Get configured provider from .env
    configured_provider = os.getenv("LLM_PROVIDER", "claude")
    print(f"🔧 Configured Provider (LLM_PROVIDER): {configured_provider}")
    print()
    
    # List all available providers
    print("="*50)
    print("Available LLM Providers:")
    print("="*50)
    
    providers = LLMFactory.list_available_providers()
    
    for provider in providers:
        status_icon = {
            "configured": "✅",
            "running": "✅",
            "missing": "❌"
        }.get(provider['status'], "⚠️")
        
        is_active = " (ACTIVE)" if provider['name'] == configured_provider else ""
        
        print(f"{status_icon} {provider['display_name']}{is_active}")
        print(f"   Status: {provider['status']}")
        print()
    
    # Recommendations
    print("="*50)
    print("💡 How to Add LLM Providers:")
    print("="*50)
    
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n📝 Claude (Anthropic):")
        print("   1. Get API key: https://console.anthropic.com/settings/keys")
        print("   2. Add to .env: ANTHROPIC_API_KEY=sk-ant-...")
    
    if not os.getenv("GEMINI_API_KEY"):
        print("\n📝 Gemini (Google):")
        print("   1. Get API key: https://makersuite.google.com/app/apikey")
        print("   2. Add to .env: GEMINI_API_KEY=your-key...")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("\n📝 OpenAI (GPT-4):")
        print("   1. Get API key: https://platform.openai.com/api-keys")
        print("   2. Add to .env: OPENAI_API_KEY=sk-...")
    
    print("\n📝 Ollama (Free, Local):")
    print("   1. Install: https://ollama.ai")
    print("   2. Run: ollama pull llama2")
    print("   3. Start: ollama serve")
    print("   4. Set in .env: LLM_PROVIDER=ollama")
    
    print("\n" + "="*50)
    print("🔄 To Switch Providers:")
    print("="*50)
    print("Edit .env and change: LLM_PROVIDER=claude")
    print("Options: claude, gemini, openai, ollama")
    print()
    
    # Test the configured provider
    if providers and providers[0]['status'] != 'missing':
        print("="*50)
        print("🧪 Testing Configured Provider...")
        print("="*50)
        
        try:
            llm = LLMFactory.create_provider()
            print(f"✅ Successfully loaded: {llm.get_provider_name()}")
            
            test_prompt = "Say 'Hello! I am working correctly.' in one sentence."
            print(f"\n🤖 Testing generation...")
            response = llm.generate(test_prompt, max_tokens=100)
            print(f"📝 Response: {response}")
            print("\n✅ LLM is working correctly!")
            
        except Exception as e:
            print(f"\n❌ Error testing provider: {e}")
            print("\n💡 Troubleshooting:")
            print("   - Check your API key is correct in .env")
            print("   - Verify you have credits/billing enabled")
            print("   - Try running: python test_setup.py")

if __name__ == "__main__":
    main()