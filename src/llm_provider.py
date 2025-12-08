"""
LLM Provider Abstraction Layer
Supports multiple LLM providers: Claude, Gemini, OpenAI, etc.
"""
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import requests
from src.config import Config


class BaseLLMProvider(ABC):
    """Base class for all LLM providers."""
    
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 4000) -> str:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name."""
        pass


class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude provider."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.anthropic.com/v1/messages"
        self.model = "claude-sonnet-4-20250514"
    
    def generate(self, prompt: str, max_tokens: int = 4000) -> str:
        """Generate text using Claude."""
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01",
                    "x-api-key": self.api_key
                },
                json={
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"Claude API error: {response.status_code} - {response.text}")
            
            data = response.json()
            return data['content'][0]['text']
            
        except Exception as e:
            raise Exception(f"Claude generation failed: {e}")
    
    def get_provider_name(self) -> str:
        return "Claude (Anthropic)"


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.model = "gemini-2.5-flash"  # Updated model name
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
    
    def generate(self, prompt: str, max_tokens: int = 4000) -> str:
        """Generate text using Gemini."""
        try:
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers={
                    "Content-Type": "application/json"
                },
                json={
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }],
                    "generationConfig": {
                        "maxOutputTokens": max_tokens,
                        "temperature": 0.7
                    }
                },
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"Gemini API error: {response.status_code} - {response.text}")
            
            data = response.json()
            
            # Handle the response structure properly
            if 'candidates' not in data or len(data['candidates']) == 0:
                raise Exception(f"No response from Gemini: {data}")
            
            candidate = data['candidates'][0]
            if 'content' not in candidate:
                raise Exception(f"Invalid response structure: {candidate}")
            
            content = candidate['content']
            if 'parts' not in content or len(content['parts']) == 0:
                raise Exception(f"No parts in response: {content}")
            
            return content['parts'][0]['text']
            
        except Exception as e:
            raise Exception(f"Gemini generation failed: {e}")
    
    def get_provider_name(self) -> str:
        return "Gemini (Google)"


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-4-turbo-preview"
    
    def generate(self, prompt: str, max_tokens: int = 4000) -> str:
        """Generate text using OpenAI GPT."""
        try:
            response = requests.post(
                self.api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens
                },
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API error: {response.status_code} - {response.text}")
            
            data = response.json()
            return data['choices'][0]['message']['content']
            
        except Exception as e:
            raise Exception(f"OpenAI generation failed: {e}")
    
    def get_provider_name(self) -> str:
        return "GPT-4 (OpenAI)"


class OllamaProvider(BaseLLMProvider):
    """Local Ollama provider (free, runs locally)."""
    
    def __init__(self, model: str = "llama2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.api_url = f"{base_url}/api/generate"
    
    def generate(self, prompt: str, max_tokens: int = 4000) -> str:
        """Generate text using local Ollama."""
        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120  # Local models can be slower
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
            
            data = response.json()
            return data['response']
            
        except Exception as e:
            raise Exception(f"Ollama generation failed: {e}")
    
    def get_provider_name(self) -> str:
        return f"Ollama ({self.model}) - Local"


class LLMFactory:
    """Factory class to create LLM providers based on configuration."""
    
    @staticmethod
    def create_provider(provider_name: str = None) -> BaseLLMProvider:
        """
        Create an LLM provider based on configuration.
        
        Args:
            provider_name: Name of provider ('claude', 'gemini', 'openai', 'ollama')
                          If None, auto-detect from available API keys
        
        Returns:
            Configured LLM provider
        """
        # Auto-detect if not specified
        if provider_name is None:
            provider_name = os.getenv("LLM_PROVIDER", "claude").lower()
        
        provider_name = provider_name.lower()
        
        # Create provider based on name
        if provider_name == "claude":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment")
            return ClaudeProvider(api_key)
        
        elif provider_name == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment")
            return GeminiProvider(api_key)
        
        elif provider_name == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            return OpenAIProvider(api_key)
        
        elif provider_name == "ollama":
            model = os.getenv("OLLAMA_MODEL", "llama2")
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            return OllamaProvider(model, base_url)
        
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")
    
    @staticmethod
    def list_available_providers() -> List[Dict[str, str]]:
        """List all available providers based on configured API keys."""
        providers = []
        
        if os.getenv("ANTHROPIC_API_KEY"):
            providers.append({
                "name": "claude",
                "display_name": "Claude (Anthropic)",
                "status": "configured"
            })
        
        if os.getenv("GEMINI_API_KEY"):
            providers.append({
                "name": "gemini",
                "display_name": "Gemini (Google)",
                "status": "configured"
            })
        
        if os.getenv("OPENAI_API_KEY"):
            providers.append({
                "name": "openai",
                "display_name": "GPT-4 (OpenAI)",
                "status": "configured"
            })
        
        # Check if Ollama is running locally
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                providers.append({
                    "name": "ollama",
                    "display_name": "Ollama (Local)",
                    "status": "running"
                })
        except:
            pass
        
        if not providers:
            providers.append({
                "name": "none",
                "display_name": "No LLM configured",
                "status": "missing"
            })
        
        return providers


# Test function
if __name__ == "__main__":
    print("Testing LLM Provider System...")
    print("\n" + "="*50)
    
    # List available providers
    available = LLMFactory.list_available_providers()
    print("Available LLM Providers:")
    for provider in available:
        print(f"  • {provider['display_name']} - {provider['status']}")
    
    print("\n" + "="*50)
    
    # Try to create a provider
    try:
        provider = LLMFactory.create_provider()
        print(f"\nUsing: {provider.get_provider_name()}")
        
        # Test generation
        print("\nTesting generation...")
        response = provider.generate("Say 'Hello, this is a test!' in one sentence.")
        print(f"Response: {response}")
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure you have at least one API key configured in .env")