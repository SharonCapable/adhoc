"""
CLI Trigger for Research Agent (Option A)

Run this from terminal to test the agent locally.
Supports multiple LLM providers: Claude, Gemini, OpenAI, Ollama
"""
import sys
import os
from src.research_agent import ResearchAgent
from src.llm_provider import LLMFactory

def main():
    print("╔═══════════════════════════════════════════════════╗")
    print("║     Research Agent - CLI Mode                     ║")
    print("╚═══════════════════════════════════════════════════╝")
    print()
    
    # Show available LLM providers
    providers = LLMFactory.list_available_providers()
    configured = os.getenv("LLM_PROVIDER", "claude")
    
    print("🤖 Available LLM Providers:")
    for p in providers:
        active = " (active)" if p['name'] == configured else ""
        print(f"   • {p['display_name']}{active}")
    print()
    
    # Ask if user wants to change provider
    print("💡 To use a different LLM, set LLM_PROVIDER in .env")
    print(f"   Current: {configured}")
    print()
    
    # Initialize agent with configured LLM
    try:
        agent = ResearchAgent()
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        print("\n💡 Try running: python check_llms.py")
        return
    
    # Interactive mode
    while True:
        print("\n" + "─" * 50)
        research_query = input("🔍 Enter your research query (or 'quit' to exit): ").strip()
        
        if research_query.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break
        
        if not research_query:
            print("❌ Please enter a valid query")
            continue
        
        try:
            # Run the research agent
            result = agent.run(research_query)
            
            # Display results
            print("\n" + "="*50)
            print("📊 RESEARCH FINDINGS")
            print("="*50)
            print(result['research_findings'])
            print("\n" + "="*50)
            
            if result.get('output_path'):
                print(f"\n💾 Full report saved to: {result['output_path']}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user. Goodbye!")
        sys.exit(0)