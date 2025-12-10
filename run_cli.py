"""
CLI Trigger for Research Agent (Option A)

Run this from terminal to test the agent locally.
Supports multiple LLM providers: Claude, Gemini, OpenAI, Ollama
"""
import sys
import os
from src.research_agent import ResearchAgent
from src.llm_provider import LLMFactory

import io

# Force UTF-8 encoding for stdout/stderr to handle emojis on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def main():
    print("===================================================")
    print("     Research Agent - CLI Mode                     ")
    print("===================================================")
    print()
    
    # Show available LLM providers
    providers = LLMFactory.list_available_providers()
    configured = os.getenv("LLM_PROVIDER", "claude")
    
    print("Available LLM Providers:")
    for p in providers:
        active = " (active)" if p['name'] == configured else ""
        print(f"   - {p['display_name']}{active}")
    print()
    
    # Ask if user wants to change provider
    # Ask if user wants to change provider
    print("To use a different LLM, set LLM_PROVIDER in .env")
    print(f"   Current: {configured}")
    print()
    
    
    # Initialize agent with configured LLM
    try:
        # Check for service account file
        service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'service-account.json')
        if not os.path.exists(service_account_file):
            print(f"[WARN] Service account file not found at: {service_account_file}")
            print("   (Google Drive framework fetching will be disabled)")
            service_account_file = None
        else:
            print(f"[OK] Found service account: {service_account_file}")

        agent = ResearchAgent(service_account_file=service_account_file)
    except Exception as e:
        print(f"Failed to initialize agent: {e}")
        print("\nTry running: python check_llms.py")
        return
    
    # Interactive mode
    while True:
        print("\n" + "-" * 50)
        research_query = input("Enter your research query (or 'quit' to exit): ").strip()
        
        if research_query.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break
        
        
        if not research_query:
            print("Please enter a valid query")
            continue
        
        try:
            # Run the research agent
            result = agent.run(research_query)
            
            # Display results
            print("\n" + "="*50)
            print("RESEARCH FINDINGS")
            print("="*50)
            print(result['research_findings'])
            print("\n" + "="*50)
            
            if result.get('output_path'):
                print(f"\n💾 Full report saved to: {result['output_path']}")
            
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)