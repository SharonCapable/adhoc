"""Google Drive integration for fetching research framework."""
import os
import io
from typing import Optional
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import pickle

from src.config import Config

# Scopes needed for Google Drive read access
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class GoogleDriveTool:
    """Tool for fetching research framework from Google Drive."""
    
    def __init__(self, service_account_file: str = None):
        """
        Initialize Google Drive tool.
        
        Args:
            service_account_file: Path to service account JSON file (optional)
                                 If not provided, falls back to OAuth
        """
        self.service = None
        self.service_account_file = service_account_file
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API using service account or OAuth."""
        
        # Try service account first (no expiry!)
        if self.service_account_file and os.path.exists(self.service_account_file):
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_file,
                    scopes=SCOPES
                )
                
                self.service = build('drive', 'v3', credentials=credentials)
                print("[OK] Google Drive authenticated with service account")
                return
            except Exception as e:
                print(f"[WARN] Service account auth failed: {e}")
                print("[INFO] Falling back to OAuth...")
        
        # Fallback to OAuth
        creds = None
        
        # Token file stores user's access and refresh tokens
        if os.path.exists(Config.GOOGLE_TOKEN_PATH):
            with open(Config.GOOGLE_TOKEN_PATH, 'rb') as token:
                creds = pickle.load(token)
        
        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    Config.GOOGLE_CREDENTIALS_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(Config.GOOGLE_TOKEN_PATH, 'wb') as token:
                pickle.dump(creds, token)
        
        self.service = build('drive', 'v3', credentials=creds)
        print("[OK] Google Drive authenticated with OAuth")
    
    def search_files(self, query: str, max_results: int = 10) -> list:
        """Search for files in Google Drive by name."""
        try:
            results = self.service.files().list(
                q=f"name contains '{query}'",
                pageSize=max_results,
                fields="files(id, name, mimeType, createdTime, modifiedTime)"
            ).execute()
            
            files = results.get('files', [])
            return files
        except Exception as e:
            print(f"Error searching files: {e}")
            return []
    
    def get_file_content(self, file_id: str) -> Optional[str]:
        """Download and return content of a text file."""
        try:
            # For Google Docs, export as plain text
            request = self.service.files().export_media(
                fileId=file_id,
                mimeType='text/plain'
            )
            
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            content = file_content.getvalue().decode('utf-8')
            return content
            
        except Exception as e:
            # If export fails, try regular download
            try:
                request = self.service.files().get_media(fileId=file_id)
                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request)
                
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                
                content = file_content.getvalue().decode('utf-8')
                return content
            except Exception as e2:
                print(f"Error downloading file: {e2}")
                return None
    
    def fetch_research_framework(self, framework_name: str = "research framework") -> Optional[str]:
        """
        Fetch the research framework document from Google Drive.
        
        Args:
            framework_name: Name or partial name of the framework document
            
        Returns:
            Content of the framework document as string
        """
        print(f"[SEARCH] Searching for framework: '{framework_name}'")
        
        files = self.search_files(framework_name)
        
        if not files:
            print(f"[ERROR] No files found matching '{framework_name}'")
            return None
        
        # Use the first matching file
        file = files[0]
        print(f"[FOUND] Found: {file['name']} (ID: {file['id']})")
        
        content = self.get_file_content(file['id'])
        
        if content:
            print(f"[OK] Framework loaded ({len(content)} characters)")
            return content
        else:
            print("[ERROR] Failed to load framework content")
            return None


# Standalone test function
if __name__ == "__main__":
    tool = GoogleDriveTool()
    framework = tool.fetch_research_framework("research framework")
    if framework:
        print("\n--- Framework Preview ---")
        print(framework[:500])