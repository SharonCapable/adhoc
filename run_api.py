"""
API Wrapper for Research Agent
Accepts JSON input via stdin and returns JSON output via stdout.
Designed to be called from Next.js API routes.

Uses Google Service Account for authentication (no token expiry issues).
"""
import sys
import json
import os

# Redirect all print() to stderr to keep stdout clean for JSON
import builtins
_original_print = builtins.print
builtins.print = lambda *args, **kwargs: _original_print(*args, **kwargs, file=sys.stderr)

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
        
        # Initialize agent with service account credentials
        agent = ResearchAgent(
            framework_source=framework_source,
            service_account_file=service_account_file if os.path.exists(service_account_file) else None
        )
        
        result = agent.run(query)
        
        # Return JSON output - use sys.stdout.write to bypass stderr redirect
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
        
        sys.stdout.write(json.dumps(output) + '\n')
        sys.stdout.flush()
        
    except Exception as e:
        import traceback
        error_output = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'success': False
        }
        sys.stdout.write(json.dumps(error_output) + '\n')
        sys.stdout.flush()
        sys.exit(1)

if __name__ == "__main__":
    main()
