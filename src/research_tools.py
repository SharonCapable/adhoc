import json
import os
import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

class GeminiGroundedSearch:
    """
    Uses the modern Google GenAI SDK (google-genai) with Google Search grounding.
    Standard for Gemini 2.5 in 2026.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
        self.model_id = os.getenv("LLM_MODEL", "gemini-2.5-flash")

    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Performs a search using Gemini with Google Search grounding.
        Returns a list of sources and a grounded summary.
        """
        print(f"[Gemini 2.5 Grounding] Searching for: '{query}'")
        
        try:
            # Enable Google Search tool
            google_search_tool = types.Tool(
                google_search=types.GoogleSearch()
            )

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=f"Research the following topic thoroughly and provide a detailed analysis based on search results: {query}",
                config=types.GenerateContentConfig(
                    tools=[google_search_tool],
                    temperature=0.0
                )
            )

            sources = []
            # Extract grounding metadata if available
            if response.candidates and response.candidates[0].grounding_metadata:
                metadata = response.candidates[0].grounding_metadata
                if metadata.search_entry_point:
                    # The SDK provides a search entry point (HTML for the "Search Google" button)
                    pass
                
                # We can extract chunks/supports here, but for now we'll take the text
                # and treat it as the findings directly.
                
            findings = response.text if response.text else "No findings generated."
            
            # Since we want to return a list of "sources" for the next nodes,
            # we'll package the grounded response as the primary source.
            return [{
                "title": "Google Search Grounded Analysis",
                "url": "https://google.com",
                "content": findings
            }]

        except Exception as e:
            print(f"[Gemini 2.5] Error: {str(e)}")
            return []

class ResearchTools:
    def __init__(self, llm_provider):
        self.llm = llm_provider
        gemini_key = os.getenv("GEMINI_API_KEY")
        self.searcher = GeminiGroundedSearch(gemini_key)

    def fetch_url_content(self, url: str, max_length: int = 5000) -> str:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            return "\n".join(chunk for chunk in chunks if chunk)
        except:
            return ""

    def search_web(self, query: str, num_results: int = 5) -> List[Dict]:
        return self.searcher.search(query, num_results=num_results)

    def analyze_sources(self, query: str, sources: List[Dict], framework: str) -> str:
        source_text = ""
        for i, s in enumerate(sources):
            source_text += f"\nSOURCE {i+1} ({s.get('url')}):\n{s.get('content')[:3000]}\n"

        prompt = f"""
        Research Query: {query}
        
        Research Framework:
        {framework}
        
        Analyzed Content from Web:
        {source_text}
        
        TASK:
        Synthesize the research findings according to the framework provided.
        Be thorough, objective, and cite sources where possible.
        Use professional markdown formatting.
        """
        return self.llm.generate(prompt)