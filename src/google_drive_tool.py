import os
import pickle
from typing import Optional
import io
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class GoogleDriveTool:
    def __init__(self, service_account_file=None):
        self.creds = None
        self.service = None
        self.service_account_file = service_account_file
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Drive API."""
        try:
            # OPTION 1: Use Service Account (Preferred for Server/Docker)
            if self.service_account_file:
                if not os.path.exists(self.service_account_file):
                    raise FileNotFoundError(f"Service account file not found: {self.service_account_file}")
                
                print(f"[INFO] Authenticating with Service Account: {self.service_account_file}")
                self.creds = service_account.Credentials.from_service_account_file(
                    self.service_account_file, scopes=SCOPES)
            
            # OPTION 2: Use OAuth User Credentials (Local Dev Fallback)
            elif os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    self.creds = pickle.load(token)
            
            # Refresh user token if expired
            if self.creds and hasattr(self.creds, 'expired') and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            
            # If no valid creds yet, try interactive login (only if credentials.json exists)
            if not self.creds and not self.service_account_file:
                if os.path.exists('credentials.json'):
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)
                    self.creds = flow.run_local_server(port=0)
                    # Save the credentials for the next run
                    with open('token.pickle', 'wb') as token:
                        pickle.dump(self.creds, token)
                else:
                    print("[WARN] No authentication method found (no service-account.json or credentials.json)")
                    return

            if self.creds:
                self.service = build('drive', 'v3', credentials=self.creds)
                print("[OK] Google Drive Service built successfully")
            else:
                print("[ERROR] Failed to obtain credentials")

        except Exception as e:
            print(f"[ERROR] Authentication failed: {str(e)}")
            raise e
            
    # ... rest of your methods (list_files, read_file, etc.)
    
    def search_files(self, query: str, max_results: int = 10) -> list:
        """Search for files in Google Drive by name."""
        if not self.service:
            print("[WARN] Google Drive service not initialized. Skipping search.")
            return []

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
        
        # Default framework if search fails or service not active
        default_framework = """
        1. Market Overview
        2. Key Competitors & Feature Comparison
        3. Pricing Models
        4. Technical Architecture & Tech Stack
        5. User Reviews & Pain Points
        6. Marketing & Growth Strategies
        """
        
        if not self.service:
            return default_framework

        files = self.search_files(framework_name)
        
        if not files:
            print(f"[WARN] No files found matching '{framework_name}'. Using default.")
            return default_framework
        
        # Use the first matching file
        file = files[0]
        print(f"[FOUND] Found: {file['name']} (ID: {file['id']})")
        
        content = self.get_file_content(file['id'])
        
        if content:
            print(f"[OK] Framework loaded ({len(content)} characters)")
            return content
        else:
            print("[ERROR] Failed to load framework content. Using default.")
            return default_framework


# Standalone test function
if __name__ == "__main__":
    tool = GoogleDriveTool()
    framework = tool.fetch_research_framework("research framework")
    if framework:
        print("\n--- Framework Preview ---")
        print(framework[:500])