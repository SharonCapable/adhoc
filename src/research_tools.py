"""
Research Tools — v2
Uses Gemini with Google Search grounding for real web results.
Falls back to Claude for analysis synthesis.
"""
import json
import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

from src.config import Config
from src.llm_provider import LLMFactory


class GeminiGroundedSearch:
    """
    Calls Gemini with Google Search grounding enabled.
    This gives real, cited search results rather than LLM-hallucinated URLs.
    Think of it like giving Gemini a live browser tab — it actually searches,
    then writes up what it found with source citations baked in.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        # Defaults to gemini-2.5-flash but can be overridden via env var
        self.model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def search(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Search with Gemini + Google Search grounding.
        Strictly returns sources from the Google Search index metadata.
        """
        prompt = (
            f"Search for: \"{query}\"\n\n"
            f"Identify the top {num_results} high-quality sources from the search results. "
            f"For each source, provide a 2-3 sentence summary of its relevance to the query."
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],   # ← grounding tool
            "generationConfig": {
                "maxOutputTokens": 2048,
                "temperature": 0.0, # Minimum temperature for grounding stability
            }
        }

        try:
            resp = requests.post(
                f"{self.url}?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()

            candidates = data.get("candidates", [])
            if not candidates:
                return []

            # STRICT EXTRACTION: Only use URLs from groundingMetadata
            # This prevents the LLM from "remembering" or "formulating" old URLs
            grounding_meta = candidates[0].get("groundingMetadata", {})
            grounding_chunks = grounding_meta.get("groundingChunks", [])
            
            results = []
            for chunk in grounding_chunks:
                web = chunk.get("web", {})
                if web.get("uri") and web.get("title"):
                    # Avoid duplicates
                    if not any(r["url"] == web["uri"] for r in results):
                        results.append({
                            "title": web["title"],
                            "url": web["uri"],
                            "summary": "Source provided by Google Search index."
                        })

            print(f"[Gemini Grounded Search] Found {len(results)} validated sources", flush=True)
            return results[:num_results]

        except Exception as e:
            print(f"[Gemini Grounded Search] Error: {e}")
            return []


class ResearchTools:
    """
    Research tools pipeline.
    Search:   Gemini 2.0 Flash with Google Search grounding (STRICTLY real URLs)
    Analysis: Configurable LLM (Claude recommended for synthesis quality)
    """

    def __init__(self, llm_provider: str = None):
        gemini_key = Config.GEMINI_API_KEY if hasattr(Config, "GEMINI_API_KEY") else None
        import os
        gemini_key = gemini_key or os.getenv("GEMINI_API_KEY")

        if gemini_key:
            self.searcher = GeminiGroundedSearch(gemini_key)
            print("🔍 Search: Gemini 2.0 Flash + Google Search grounding (Strict Mode)", flush=True)
        else:
            self.searcher = None
            print("❌ ERROR: GEMINI_API_KEY not set. Search disabled.", flush=True)

        try:
            self.llm = LLMFactory.create_provider(llm_provider)
            print(f"🤖 Analysis LLM: {self.llm.get_provider_name()}", flush=True)
        except Exception as e:
            print(f"❌ Failed to initialise analysis LLM: {e}")
            raise

    def search_web(self, query: str, num_results: int = 5) -> List[Dict]:
        """
        Search the web using Gemini grounding. 
        NO LLM FALLBACK: If no real URLs are found, returns an empty list.
        """
        if not self.searcher:
            print("[Search] Searcher not initialized. Check API keys.")
            return []

        results = self.searcher.search(query, num_results)
        if not results:
            print(f"[Search] No real results found for: '{query}' in Google index.", flush=True)
        
        return results


    def fetch_url_content(self, url: str, max_length: int = 5000) -> Optional[str]:
        """Fetch and extract text content from a URL."""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Adhoc Research Bot)"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = " ".join(soup.get_text().split())
            return text[:max_length] + ("..." if len(text) > max_length else "")
        except Exception as e:
            print(f"[Fetch] Error fetching {url}: {e}")
            return None

    def analyze_sources(self, sources: List[Dict], research_question: str, framework: str = "") -> str:
        """
        Synthesise sources into a structured research report.
        Uses the analysis LLM (Claude by default for quality).
        """
        print(f"[Analyze] Synthesising {len(sources)} sources...", flush=True)

        if not sources:
            return "No sources available. The search returned no results."

        sources_text = "\n\n".join([
            f"SOURCE {i+1}: {s['title']}\nURL: {s['url']}\nCONTENT: {s.get('content') or s.get('summary', '')}"
            for i, s in enumerate(sources)
        ])

        framework_section = f"\n\nRESEARCH FRAMEWORK:\n{framework}" if framework else ""

        prompt = f"""You are a senior research analyst at AyaData AI Solutions — a team that builds AI-powered software products including speech models, computer vision systems, LLM pipelines, and client-facing AI products.

RESEARCH QUESTION: {research_question}
{framework_section}

SOURCES:
{sources_text}

Produce a structured research report. Determine the correct output type from:
- Market Analysis
- Technical Analysis  
- Comparative Analysis
- Domain Intelligence Report
- Solution Design Brief

State the output type at the top. Then follow the appropriate section structure.

ALWAYS end with an "IMPLICATIONS FOR AI SOLUTIONS" section — specific, actionable, grounded in the team's actual product context (speech models, CV, LLM systems, client product builds).

FORMATTING:
- Section headers in UPPERCASE
- Numbered lists only (no bullet dashes)
- Citations as [Source N](URL) inline
- No markdown bold (**text**)
- End with a numbered REFERENCES section"""

        try:
            analysis = self.llm.generate(prompt, max_tokens=4000)
            print(f"[Analyze] Complete ({len(analysis)} chars)", flush=True)
            return analysis
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"Analysis error: {e}"