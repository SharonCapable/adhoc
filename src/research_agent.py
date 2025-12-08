"""LangGraph Research Agent - The core orchestration logic."""
from typing import Dict
from langgraph.graph import StateGraph, END
import json
from datetime import datetime

from src.agent_state import ResearchState
from src.google_drive_tool import GoogleDriveTool
from src.research_tools import ResearchTools
from src.config import Config
from src.qa_validator import QAValidator

from google.oauth2 import service_account
from googleapiclient.discovery import build

class ResearchAgent:
    """
    The main research agent using LangGraph.
    
    Think of this as the head chef coordinating all kitchen stations:
    1. Fetch Framework (get the cookbook)
    2. Search Web (find ingredients)
    3. Fetch Content (prepare ingredients)
    4. Analyze (cook the dish)
    5. Save Output (plate and serve)
    """
    def __init__(self, framework_source=None, service_account_file=None, llm_provider: str = None):
        """
        Initialize research agent.
        
        Args:
            framework_source: Optional Google Drive file/folder ID for research framework
            service_account_file: Path to Google service account JSON file
            llm_provider: LLM provider to use ('claude', 'gemini', 'openai', 'ollama')
                         If None, uses the one configured in .env
        """
        self.framework_source = framework_source
        self.service_account_file = service_account_file
        self.drive_service = None
        
        # Initialize Google Drive if we have a framework source
        if framework_source and service_account_file:
            self._init_google_drive_with_service_account()
        elif framework_source:
            # Fallback to OAuth if no service account (for backward compatibility)
            self._init_google_drive_oauth()
        
        # Initialize research tools
        self.drive_tool = GoogleDriveTool(service_account_file=service_account_file)
        self.research_tools = ResearchTools(llm_provider)
        self.graph = self._build_graph()
    
    def _init_google_drive_with_service_account(self):
        """Initialize Google Drive API with service account (no expiry!)"""
        try:
            SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
            
            credentials = service_account.Credentials.from_service_account_file(
                self.service_account_file,
                scopes=SCOPES
            )
            
            self.drive_service = build('drive', 'v3', credentials=credentials)
            print("[OK] Google Drive initialized with service account")
            
        except Exception as e:
            print(f"[ERROR] Failed to initialize Google Drive: {e}")
            self.drive_service = None
    
    def _init_google_drive_oauth(self):
        """Fallback OAuth method (has token expiry issues)"""
        # Your existing OAuth code here
        pass
    

    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Create the graph
        workflow = StateGraph(ResearchState)
        
        # Add nodes (each node is a function/station)
        workflow.add_node("fetch_framework", self.fetch_framework_node)
        workflow.add_node("search_web", self.search_web_node)
        workflow.add_node("fetch_content", self.fetch_content_node)
        workflow.add_node("qa_validate", self.qa_validate_node)
        workflow.add_node("analyze", self.analyze_node)
        workflow.add_node("save_output", self.save_output_node)
        
        # Define the flow (edges)
        workflow.set_entry_point("fetch_framework")
        workflow.add_edge("fetch_framework", "search_web")
        workflow.add_edge("search_web", "fetch_content")
        workflow.add_edge("fetch_content", "qa_validate")
        workflow.add_edge("qa_validate", "analyze")
        workflow.add_edge("analyze", "save_output")
        workflow.add_edge("save_output", END)
        
        return workflow.compile()
    
    # Node 1: Fetch Research Framework
    def fetch_framework_node(self, state: ResearchState) -> Dict:
        """Load research framework from Google Drive."""
        print("\n📚 [Node 1] Fetching research framework...")
        
        try:
            framework = self.drive_tool.fetch_research_framework()
            
            if framework:
                return {
                    "framework_loaded": True,
                    "framework_content": framework,
                    "status": "framework_loaded"
                }
            else:
                # Framework is optional, proceed without it
                print("⚠️  No framework found, proceeding without guidelines")
                return {
                    "framework_loaded": False,
                    "framework_content": "",
                    "status": "framework_not_found"
                }
        except Exception as e:
            print(f"❌ Error loading framework: {e}")
            return {
                "framework_loaded": False,
                "framework_content": "",
                "status": "framework_error",
                "error_message": str(e)
            }
    
    # Node 2: Search the Web
    def search_web_node(self, state: ResearchState) -> Dict:
        """Search for relevant sources."""
        print("\n🔍 [Node 2] Searching the web...")
        
        query = state["research_query"]
        
        try:
            results = self.research_tools.search_web(
                query,
                num_results=Config.MAX_SEARCH_RESULTS
            )
            
            print(f"✅ Found {len(results)} sources")
            for i, r in enumerate(results, 1):
                print(f"  {i}. {r['title']}")
            
            return {
                "search_results": results,
                "status": "search_complete"
            }
        except Exception as e:
            print(f"❌ Search error: {e}")
            return {
                "search_results": [],
                "status": "search_error",
                "error_message": str(e)
            }
    
    # Node 3: Fetch Full Content from URLs
    def fetch_content_node(self, state: ResearchState) -> Dict:
        """Fetch full content from search result URLs."""
        print("\n📥 [Node 3] Fetching content from sources...")
        
        search_results = state.get("search_results", [])
        sources_with_content = []
        
        for i, result in enumerate(search_results, 1):
            print(f"  Fetching {i}/{len(search_results)}: {result['title']}")
            
            content = self.research_tools.fetch_url_content(
                result['url'],
                max_length=Config.MAX_CONTENT_LENGTH
            )
            
            source = {
                "title": result['title'],
                "url": result['url'],
                "summary": result.get('summary', ''),
                "content": content if content else result.get('summary', '')
            }
            sources_with_content.append(source)
        
        print(f"✅ Content fetched from {len(sources_with_content)} sources")
        
        return {
            "sources_with_content": sources_with_content,
            "status": "content_fetched"
        }
    
    # Node 4: QA Validation
    def qa_validate_node(self, state: ResearchState) -> Dict:
        """Validate source relevance and check for quality issues."""
        print("\n✅ [Node 4] Running QA validation...")
        
        sources = state.get("sources_with_content", [])
        query = state["research_query"]
        
        try:
            validator = QAValidator(query)
            valid_sources, rejected_sources, reasons = validator.validate_sources(sources)
            
            # Log validation details
            print(f"\n📋 Source Validation Results:")
            for reason in reasons:
                print(f"  {reason}")
            
            print(f"\n✅ Validated: {len(valid_sources)} sources passed")
            if rejected_sources:
                print(f"⚠️  Rejected: {len(rejected_sources)} sources failed validation")
            
            return {
                "sources_with_content": valid_sources,
                "rejected_sources": rejected_sources,
                "qa_validation_details": reasons,
                "status": "qa_validated"
            }
        except Exception as e:
            print(f"❌ QA validation error: {e}")
            # If validation fails, continue with original sources
            return {
                "sources_with_content": sources,
                "qa_validation_details": [f"Validation error: {str(e)}"],
                "status": "qa_validation_error"
            }
    
    # Node 5: Analyze and Synthesize
    def analyze_node(self, state: ResearchState) -> Dict:
        """Analyze sources and generate research findings."""
        print("\n🧠 [Node 5] Analyzing sources...")
        
        sources = state.get("sources_with_content", [])
        query = state["research_query"]
        framework = state.get("framework_content", "")
        
        try:
            findings = self.research_tools.analyze_sources(
                sources,
                query,
                framework
            )
            
            # Validate reasoning quality
            validator = QAValidator(query)
            findings_validation = validator.validate_findings(findings, sources)
            
            if not findings_validation["is_valid"]:
                print(f"\n⚠️  {findings_validation['message']}")
            else:
                print(f"\n✅ Reasoning quality passed: {findings_validation['quality_score']:.1%}")
            
            print("✅ Analysis complete")
            
            return {
                "research_findings": findings,
                "findings_qa": findings_validation,
                "status": "analysis_complete"
            }
        except Exception as e:
            print(f"❌ Analysis error: {e}")
            return {
                "research_findings": f"Error during analysis: {e}",
                "status": "analysis_error",
                "error_message": str(e)
            }
    
    # Node 5: Save Output
    def save_output_node(self, state: ResearchState) -> Dict:
        """Save research findings to file with embedded sources and QA report."""
        print("\n💾 [Node 6] Saving output...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"research_{timestamp}.json"
        filepath = Config.OUTPUT_DIR / filename
        
        # Extract sources for embedding
        sources = state.get("sources_with_content", [])
        
        output_data = {
            "research_query": state["research_query"],
            "timestamp": timestamp,
            "framework_used": state.get("framework_loaded", False),
            "sources": sources,
            "findings": state.get("research_findings", ""),
            "qa_validation": {
                "sources_qa": {
                    "validation_details": state.get("qa_validation_details", []),
                    "rejected_sources": state.get("rejected_sources", [])
                },
                "findings_qa": state.get("findings_qa", {})
            },
            "status": state.get("status", "unknown")
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Output saved to: {filepath}")
            
            # Also save a markdown version for easy reading with embedded sources
            md_filename = f"research_{timestamp}.md"
            md_filepath = Config.OUTPUT_DIR / md_filename
            
            with open(md_filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Research Report\n\n")
                f.write(f"**Query:** {state['research_query']}\n\n")
                f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"---\n\n")
                f.write(f"## Findings\n\n")
                f.write(state.get("research_findings", "No findings"))
                f.write(f"\n\n---\n\n## Sources\n\n")
                
                # Embed sources with titles and links
                for i, source in enumerate(sources, 1):
                    title = source.get('title', 'Untitled')
                    url = source.get('url', '')
                    summary = source.get('summary', '')
                    
                    f.write(f"### {i}. {title}\n\n")
                    if url:
                        f.write(f"**Link:** [{url}]({url})\n\n")
                    if summary:
                        f.write(f"**Summary:** {summary}\n\n")
                    f.write(f"\n")
            
            print(f"✅ Markdown saved to: {md_filepath}")
            
            return {
                "output_path": str(filepath),
                "status": "complete"
            }
        except Exception as e:
            print(f"❌ Save error: {e}")
            return {
                "status": "error",
                "error_message": str(e)
            }
    
    def run(self, research_query: str) -> Dict:
        """
        Execute the research workflow.
        
        Args:
            research_query: The research question/topic
            
        Returns:
            Final state with results
        """
        print(f"\n{'='*60}")
        print(f"🚀 Starting Research Agent")
        print(f"{'='*60}")
        print(f"Query: {research_query}\n")
        
        # Initial state
        initial_state = {
            "research_query": research_query,
            "framework_loaded": False,
            "framework_content": "",
            "search_results": [],
            "sources_with_content": [],
            "research_findings": "",
            "status": "initializing",
            "error_message": None,
            "output_path": None
        }
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        print(f"\n{'='*60}")
        print(f"✅ Research Complete!")
        print(f"{'='*60}")
        print(f"Status: {final_state['status']}")
        if final_state.get('output_path'):
            print(f"Output: {final_state['output_path']}")
        
        return final_state


# Test the agent
if __name__ == "__main__":
    agent = ResearchAgent()
    result = agent.run("What are the latest trends in AI-powered education technology?")
    
    print("\n--- Research Findings Preview ---")
    print(result['research_findings'][:500])