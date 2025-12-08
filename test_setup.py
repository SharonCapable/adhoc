"""
Test script to verify your setup is working correctly.
Run this before using the agent to catch configuration issues early.
"""
import os
import sys
from pathlib import Path

def test_imports():
    """Test that all required packages are installed."""
    print("\n[PACKAGES] Testing imports...")
    try:
        import langchain
        import langgraph
        import requests
        from google.oauth2.credentials import Credentials
        from slack_bolt import App
        from bs4 import BeautifulSoup
        print("   [OK] All packages imported successfully")
        return True
    except ImportError as e:
        print(f"   [FAIL] Import error: {e}")
        print("   [TIP] Run: pip install -r requirements.txt")
        return False

def test_env_file():
    """Test that .env file exists and has required variables."""
    print("\n[ENV] Testing environment configuration...")
    
    if not Path(".env").exists():
        print("   [FAIL] .env file not found")
        print("   [TIP] Copy .env.template to .env and fill in your API keys")
        return False
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = {
        "ANTHROPIC_API_KEY": "Claude API key"
    }
    
    missing = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing.append(f"{var} ({description})")
    
    if missing:
        print("   [FAIL] Missing required environment variables:")
        for var in missing:
            print(f"      - {var}")
        return False
    
    print("   [OK] Environment variables configured")
    return True

def test_google_credentials():
    """Test Google Drive credentials."""
    print("\n[GOOGLE] Testing Google Drive credentials...")
    
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    
    if not Path(creds_path).exists():
        print(f"   [WARN] {creds_path} not found")
        print("   [TIP] Download OAuth credentials from Google Cloud Console")
        print("   [INFO] Agent will work without it, but won't fetch framework")
        return False
    
    print(f"   [OK] Found {creds_path}")
    return True

def test_directories():
    """Test that required directories exist."""
    print("\n[DIRS] Testing directory structure...")
    
    required_dirs = [
        "src",
        "data/outputs"
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        path = Path(dir_path)
        if not path.exists():
            print(f"   [FAIL] Missing directory: {dir_path}")
            print(f"   [CREATE] Creating: {dir_path}")
            path.mkdir(parents=True, exist_ok=True)
        else:
            print(f"   [OK] {dir_path} exists")
    
    return True

def test_config():
    """Test that config module loads correctly."""
    print("\n[CONFIG] Testing configuration module...")
    try:
        from src.config import Config
        print("   [OK] Config module loaded")
        return True
    except Exception as e:
        print(f"   [FAIL] Error loading config: {e}")
        return False

def test_anthropic_api():
    """Test that Anthropic API key works."""
    print("\n[API] Testing Claude API connection...")
    try:
        import requests
        from src.config import Config
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": Config.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Hi"}]
            }
        )
        
        if response.status_code == 200:
            print("   [OK] Claude API connection successful")
            return True
        elif response.status_code == 401:
            print("   [FAIL] Invalid API key")
            return False
        else:
            print(f"   [WARN] API returned status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   [FAIL] Error testing API: {e}")
        return False

def test_slack_config():
    """Test Slack configuration (optional)."""
    print("\n[SLACK] Testing Slack configuration...")
    
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    slack_app_token = os.getenv("SLACK_APP_TOKEN")
    
    if not slack_token or not slack_app_token:
        print("   [INFO] Slack not configured (optional)")
        print("   [TIP] Add SLACK_BOT_TOKEN and SLACK_APP_TOKEN to .env for Slack integration")
        return None
    
    print("   [OK] Slack tokens found")
    return True

def main():
    """Run all tests."""
    print("=" * 55)
    print("   Research Agent - Setup Test")
    print("=" * 55)
    
    tests = [
        ("Package Imports", test_imports),
        ("Environment File", test_env_file),
        ("Google Credentials", test_google_credentials),
        ("Directory Structure", test_directories),
        ("Config Module", test_config),
        ("Claude API", test_anthropic_api),
        ("Slack Config", test_slack_config),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            result = test_func()
            results[name] = result
        except Exception as e:
            print(f"\n   [ERROR] Unexpected error in {name}: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*50)
    print("[SUMMARY] TEST SUMMARY")
    print("="*50)
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    
    for name, result in results.items():
        if result is True:
            status = "[PASS]"
        elif result is False:
            status = "[FAIL]"
        else:
            status = "[SKIP]"
        print(f"{status} - {name}")
    
    print("="*50)
    print(f"Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    print("="*50)
    
    if failed == 0:
        print("\n[SUCCESS] All critical tests passed! You're ready to run the agent.")
        print("\nNext steps:")
        print("   - CLI mode: python run_cli.py")
        print("   - Slack mode: python run_slack.py")
        return 0
    else:
        print("\n[WARNING] Some tests failed. Please fix the issues above before running the agent.")
        return 1

if __name__ == "__main__":
    sys.exit(main())