"""State management for the LangGraph research agent."""
from typing import TypedDict, List, Dict, Optional

class ResearchState(TypedDict, total=False):
    """
    The state that flows through the agent graph.
    
    Think of this as the clipboard that gets passed between
    different stations in a kitchen - each station reads it,
    does their work, and updates it for the next station.
    """
    
    # Input
    research_query: str  # What the user wants to research
    
    # Framework
    framework_loaded: bool  # Has the framework been loaded?
    framework_content: str  # The research framework from Google Drive
    
    # Search results
    search_results: List[Dict]  # Raw search results
    sources_with_content: List[Dict]  # Sources with full content fetched
    
    # QA Validation
    rejected_sources: List[Dict]  # Sources that failed QA validation
    qa_validation_details: List[str]  # QA validation reasoning
    
    # Analysis
    research_findings: str  # Synthesized research output
    findings_qa: Dict  # QA validation results for findings
    
    # Metadata
    status: str  # Current status (searching, analyzing, complete, error)
    error_message: Optional[str]  # Error details if any
    output_path: Optional[str]  # Path to output file
    
    # Output
    output_path: Optional[str]  # Path to saved output file