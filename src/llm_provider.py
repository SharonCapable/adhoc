import os
from google import genai
from google.genai import types

class GeminiProvider:
    """
    LLM Provider using the modern google-genai SDK.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        self.model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    
    def generate(self, prompt: str, max_tokens: int = 4000) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=max_tokens,
                    temperature=0.7
                )
            )
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"

class AnthropicProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022")
    
    def generate(self, prompt: str, max_tokens: int = 4000) -> str:
        # Fallback to Claude if needed (uses requests or anthropic SDK)
        import requests
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        data = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()["content"][0]["text"]
        return f"Error: {response.text}"

def get_llm_provider():
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider_type == "gemini":
        return GeminiProvider(os.getenv("GEMINI_API_KEY"))
    else:
        return AnthropicProvider(os.getenv("ANTHROPIC_API_KEY"))