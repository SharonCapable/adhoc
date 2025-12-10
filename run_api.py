"""
API Wrapper for Research Agent
Accepts JSON input via stdin and returns JSON output via stdout.
Designed to be called from Next.js API routes.

Uses Google Service Account for authentication (no token expiry issues).
"""
import sys
import json
import os

# Helper for detailed logging
def log(msg):
    sys.stderr.write(f"{str(msg)}\n")
    sys.stderr.flush()

# KEY FIX: Redirect actual stdout to stderr globally to prevent ANY logs from sticking to JSON output
# keep a handle to the real stdout to print the final JSON later
_REAL_STDOUT = sys.stdout
sys.stdout = sys.stderr

from src.research_agent import ResearchAgent

def main():
    try:
        # Read JSON input from stdin
        input_data = json.loads(sys.stdin.read())
        
        query = input_data.get('query', '')
        framework_source = input_data.get('frameworkSource')
        
        if not query:
            sys.stdout.write(json.dumps({
                'error': 'Query is required',
                'success': False
            }) + '\n')
            sys.stdout.flush()
            sys.exit(1)
        
        # Get service account credentials from environment or file
        service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'service-account.json')
        
        # DEBUG: Check if file exists and what is in the dir
        cwd = os.getcwd()
        log(f"[DEBUG] CWD: {cwd}")
        try:
            log(f"[DEBUG] Files in CWD: {os.listdir(cwd)}")
        except Exception:
            pass

        if os.path.exists(service_account_file):
            log(f"[DEBUG] Found service account file: {service_account_file}")
        else:
            log(f"[DEBUG] Service account file NOT found: {service_account_file}")
            env_val = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON', '')
            log(f"[DEBUG] GOOGLE_SERVICE_ACCOUNT_JSON env var length: {len(env_val)}")
            
            # SELF-HEALING: Write the file if env var exists but file is missing
            if env_val:
                log("[INFO] Creating service-account.json from environment variable...")
                try:
                    with open(service_account_file, 'w') as f:
                        f.write(env_val)
                    log(f"[OK] Successfully created {service_account_file}")
                except Exception as write_err:
                    log(f"[ERROR] Failed to write service account file: {write_err}")

        
        # Initialize agent with service account credentials
        agent = ResearchAgent(
            framework_source=framework_source,
            service_account_file=service_account_file if os.path.exists(service_account_file) else None
        )
        
        # Remove the re-apply block as global sys.stdout reuse handles it 


        result = agent.run(query)
        
        # Return JSON output - use _REAL_STDOUT to ensure it goes to the pipe
        output = {
            'success': True,
            'research_findings': result.get('research_findings', ''),
            'output_path': result.get('output_path', ''),
            'status': result.get('status', ''),
            'framework_loaded': result.get('framework_loaded', False),
            'sources_count': len(result.get('sources_with_content', [])),
            'error_message': result.get('error_message'),
            'validation_warnings': result.get('qa_validation_details', [])
        }
        
        _REAL_STDOUT.write(json.dumps(output) + '\n')
        _REAL_STDOUT.flush()
        
    except Exception as e:
        import traceback
        error_output = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'success': False
        }
        _REAL_STDOUT.write(json.dumps(error_output) + '\n')
        _REAL_STDOUT.flush()
        sys.exit(1)

if __name__ == "__main__":
    main()
