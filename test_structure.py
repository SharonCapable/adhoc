"""
Test the agent structure without making API calls.
This verifies your setup is correct before adding credits.
"""
from src.google_drive_tool import GoogleDriveTool
from src.config import Config
import json

def test_google_drive():
    """Test Google Drive connection."""
    print("\n" + "="*50)
    print("Testing Google Drive Connection")
    print("="*50)
    
    try:
        drive_tool = GoogleDriveTool()
        print("✅ Google Drive tool initialized")
        
        # Try to search for your research framework
        framework = drive_tool.fetch_research_framework("research framework")
        
        if framework:
            print(f"✅ Framework loaded: {len(framework)} characters")
            print("\n--- Framework Preview (first 300 chars) ---")
            print(framework[:300])
            print("...")
        else:
            print("⚠️  No framework found (this is okay for testing)")
            print("💡 Create a Google Doc named 'research framework' to test")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_config():
    """Test configuration."""
    print("\n" + "="*50)
    print("Testing Configuration")
    print("="*50)
    
    print(f"Output Directory: {Config.OUTPUT_DIR}")
    print(f"Max Search Results: {Config.MAX_SEARCH_RESULTS}")
    print(f"Max Content Length: {Config.MAX_CONTENT_LENGTH}")
    
    # Check if output directory exists
    if Config.OUTPUT_DIR.exists():
        print(f"✅ Output directory exists: {Config.OUTPUT_DIR}")
    else:
        Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created output directory: {Config.OUTPUT_DIR}")
    
    return True

def test_save_output():
    """Test saving output to file."""
    print("\n" + "="*50)
    print("Testing File Output")
    print("="*50)
    
    test_data = {
        "research_query": "Test query",
        "timestamp": "20241117_120000",
        "framework_used": True,
        "sources": [
            {
                "title": "Test Source",
                "url": "https://example.com",
                "summary": "This is a test"
            }
        ],
        "findings": "These are test findings.",
        "status": "complete"
    }
    
    try:
        output_file = Config.OUTPUT_DIR / "test_output.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, indent=2)
        
        print(f"✅ Successfully wrote test file: {output_file}")
        
        # Read it back
        with open(output_file, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        
        print(f"✅ Successfully read test file")
        print(f"   Query: {loaded_data['research_query']}")
        print(f"   Sources: {len(loaded_data['sources'])}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all structure tests."""
    print("╔═══════════════════════════════════════════════════╗")
    print("║   Research Agent - Structure Test                ║")
    print("║   (No API calls required)                         ║")
    print("╚═══════════════════════════════════════════════════╝")
    
    results = []
    
    # Test configuration
    results.append(("Configuration", test_config()))
    
    # Test Google Drive
    results.append(("Google Drive", test_google_drive()))
    
    # Test file output
    results.append(("File Output", test_save_output()))
    
    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print("="*50)
    print(f"Passed: {passed}/{total}")
    print("="*50)
    
    if passed == total:
        print("\n🎉 All structure tests passed!")
        print("\n📝 Next steps:")
        print("   1. Add credits to your Claude API account")
        print("   2. Update your API key in .env if needed")
        print("   3. Run: python run_cli.py")
    else:
        print("\n⚠️  Some tests failed. Fix the issues above.")

if __name__ == "__main__":
    main()