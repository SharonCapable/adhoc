"""Research tools using any LLM provider (Claude, Gemini, OpenAI, etc.)."""
import json
import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from src.config import Config
from src.llm_provider import LLMFactory

class ResearchTools:
    """Tools for conducting web research using any LLM provider."""
    
    def __init__(self, llm_provider: str = None):
        """
        Initialize research tools.
        
        Args:
            llm_provider: LLM provider to use ('claude', 'gemini', 'openai', 'ollama')
                         If None, uses the one configured in .env
        """
        try:
            self.llm = LLMFactory.create_provider(llm_provider)
            self.llm = LLMFactory.create_provider(llm_provider)
            print(f"🤖 Using LLM: {self.llm.get_provider_name()}", flush=True)
        except Exception as e:
            print(f"❌ Failed to initialize LLM: {e}")
            raise
    
    def search_web(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Use LLM to search the web for information.
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of search results with titles, URLs, and snippets
        """
        print(f"🔍 Searching for: '{query}'", flush=True)
        
        prompt = f"""Search the web for: "{query}"

Provide exactly {num_results} relevant sources. For each source, return:
1. Title of the page
2. URL
3. Brief summary (2-3 sentences)

Format your response as JSON:
{{
  "results": [
    {{
      "title": "...",
      "url": "...",
      "summary": "..."
    }}
  ]
}}

IMPORTANT: Your response must be ONLY valid JSON, nothing else. No markdown, no explanations."""

        try:
            # Use the configured LLM provider
            print(f"📡 Sending request to {self.llm.get_provider_name()}...", flush=True)
            response_text = self.llm.generate(prompt, max_tokens=4000)
            print(f"✅ Received response ({len(response_text)} chars)", flush=True)
            
            # Clean up response (remove markdown if present)
            content = response_text.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            # Parse JSON
            print(f"🔄 Parsing JSON response...", flush=True)
            results = json.loads(content)

            # Support multiple response shapes from different LLMs.
            # Some LLMs may return a dict with a 'results' key, others may return
            # a list of result objects directly. Handle both to avoid AttributeError.
            parsed_results = []
            if isinstance(results, dict):
                parsed_results = results.get('results', [])
            elif isinstance(results, list):
                # If it's a list of result dicts, use it directly
                if results and isinstance(results[0], dict) and any(k in results[0] for k in ('title', 'url', 'summary')):
                    parsed_results = results
                # If it's a single-element list that contains a dict with 'results'
                elif len(results) == 1 and isinstance(results[0], dict) and 'results' in results[0]:
                    parsed_results = results[0].get('results', [])
                else:
                    # Unknown list format; attempt to use it as-is
                    parsed_results = results
            else:
                parsed_results = []
            
            print(f"✅ Found {len(parsed_results)} results", flush=True)
            return parsed_results
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"📄 Raw response preview: {response_text[:200] if 'response_text' in locals() else 'No response'}")
            return []
        except AttributeError as e:
            print(f"❌ Attribute error: {e}")
            print(f"💡 LLM object type: {type(self.llm)}")
            print(f"💡 LLM has generate method: {hasattr(self.llm, 'generate')}")
            return []
        except Exception as e:
            print(f"❌ Search error: {type(e).__name__}: {e}")
            import traceback
            print("📋 Full traceback:")
            traceback.print_exc()
            return []
    
    def fetch_url_content(self, url: str, max_length: int = 5000) -> Optional[str]:
        """
        Fetch content from a URL and extract text.
        
        Args:
            url: URL to fetch
            max_length: Maximum characters to return
            
        Returns:
            Extracted text content
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Research Agent)'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML - use html.parser (built-in, no C compiler needed)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Truncate if needed
            if len(text) > max_length:
                text = text[:max_length] + "..."
            
            return text
            
        except Exception as e:
            print(f"❌ Error fetching {url}: {e}")
            return None
    
    def analyze_sources(self, sources: List[Dict], research_question: str, framework: str = "") -> str:
        """
        Use LLM to analyze multiple sources and extract key information.
        
        Args:
            sources: List of sources with content
            research_question: The research question being answered
            framework: Research framework guidelines (optional)
            
        Returns:
            Synthesized research findings
        """
        print(f"🧠 Analyzing {len(sources)} sources...", flush=True)
        
        if not sources:
            return "No sources available to analyze. The web search returned no results."
        
        sources_text = "\n\n".join([
            f"SOURCE {i+1}: {s['title']}\nURL: {s['url']}\nCONTENT: {s.get('content', s.get('summary', ''))}"
            for i, s in enumerate(sources)
        ])
        
        framework_section = f"\n\nRESEARCH FRAMEWORK:\n{framework}" if framework else ""
        
        prompt = f"""You are a research analyst. Analyze the following sources to answer this research question:
        
RESEARCH QUESTION: {research_question}
{framework_section}

SOURCES:
{sources_text}

Based on these sources, provide a comprehensive research report with:
1. Executive Summary
2. Key Findings (bullet points)
3. Detailed Analysis (Themes, Patterns, Data)
4. Source Reliability Assessment

FORMATTING RULES:
- Use CLEAN formatting. Avoid excessive markdown symbols like '###' or '***'.
FORMATTING RULES:
- Use CLEAN formatting with uppercase section labels.
- CITATIONS: You MUST use standard Markdown links: [Source N](URL).
  - CORRECT: "Matches [Source 1](https://google.com)" -> Renders as clickable "Source 1".
  - WRONG: "Source 1 (https://google.com)" -> DO NOT DO THIS.
  - WRONG: "[Source 1]" without a link -> DO NOT DO THIS.
- When listing multiple, comma-separate them: ([Source 1](URL), [Source 2](URL)).
- Failure to hide the URL inside the link syntax is a critical error.
- Keep the design professional."""

        try:
            print(f"📡 Sending analysis request to {self.llm.get_provider_name()}...", flush=True)
            analysis = self.llm.generate(prompt, max_tokens=4000)
            print(f"✅ Analysis complete ({len(analysis)} chars)", flush=True)
            return analysis
            
        except Exception as e:
            error_msg = f"Error during analysis: {type(e).__name__}: {e}"
            print(f"❌ {error_msg}")
            import traceback
            print("📋 Full traceback:")
            traceback.print_exc()
            return error_msg


# Test function
if __name__ == "__main__":
    from src.llm_provider import LLMFactory
    
    # Test with configured LLM
    print("Testing ResearchTools...")
    tools = ResearchTools()
    
    # Test search
    print("\nTesting web search...")
    results = tools.search_web("AI in education trends 2024", num_results=3)
    for r in results:
        print(f"- {r['title']}: {r['url']}")
    
    # Test URL fetch
    if results:
        print(f"\nTesting URL fetch...")
        content = tools.fetch_url_content(results[0]['url'])
        if content:
            print(f"Fetched {len(content)} characters")