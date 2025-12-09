"""Configuration management for the research agent."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Central configuration for the research agent."""
    
    # API Keys
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    
    # Google Drive
    GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    GOOGLE_TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
    
    # Slack (for Option B)
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
    SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
    
    # Output directory
    OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./data/outputs"))
    
    # Research settings
    MAX_SEARCH_RESULTS = 5
    MAX_CONTENT_LENGTH = 5000  # Max chars to extract from each source
    
    @classmethod
    def validate(cls):
        """Validate that required configurations are present."""
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        
        if not Path(cls.GOOGLE_CREDENTIALS_PATH).exists():
            # Just warn, don't raise error, as we might be using service_account passed directly
            print(f"[WARN] Google credentials not found at {cls.GOOGLE_CREDENTIALS_PATH}")
            # raise ValueError(f"Google credentials not found at {cls.GOOGLE_CREDENTIALS_PATH}")
        
        # Create output directory if it doesn't exist
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        return True

# Validate on import
try:
    Config.validate()
    print("[OK] Configuration validated successfully")
except ValueError as e:
    print(f"[WARN] Configuration warning: {e}")