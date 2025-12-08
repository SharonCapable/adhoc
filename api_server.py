# Improved api_server.py with better error handling and logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
import os
import json
import subprocess
import traceback
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResearchRequest(BaseModel):
    query: str
    frameworkSource: Optional[str] = None

@app.post("/research")
async def run_research(request: ResearchRequest):
    logger.info(f"Received research request: {request.query[:50]}...")
    
    try:
        # Prepare input data
        input_data = json.dumps({
            "query": request.query,
            "frameworkSource": request.frameworkSource
        })
        
        logger.info("Starting subprocess...")
        
        # Run existing script as subprocess
        process = subprocess.Popen(
            [sys.executable, "run_api.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        logger.info("Communicating with subprocess...")
        stdout, stderr = process.communicate(input=input_data, timeout=120)
        
        logger.info(f"Subprocess completed with return code: {process.returncode}")
        
        if stderr:
            logger.warning(f"Subprocess stderr: {stderr}")
        
        if process.returncode != 0:
            logger.error(f"Script failed with code {process.returncode}")
            logger.error(f"Stderr: {stderr}")
            logger.error(f"Stdout: {stdout}")
            raise HTTPException(
                status_code=500, 
                detail={
                    "error": "Script execution failed",
                    "return_code": process.returncode,
                    "stderr": stderr,
                    "stdout": stdout[:500] if stdout else None
                }
            )
        
        logger.info("Parsing JSON output...")
        try:
            result = json.loads(stdout)
            logger.info("Successfully parsed JSON response")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Raw output: {stdout[:500]}")
            return {
                "success": False, 
                "error": "Invalid JSON output from script",
                "raw_output": stdout[:500],
                "parse_error": str(e)
            }

    except subprocess.TimeoutExpired:
        logger.error("Subprocess timeout")
        process.kill()
        raise HTTPException(status_code=504, detail="Research request timed out after 120 seconds")
    
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        )

@app.get("/health")
def health_check():
    logger.info("Health check called")
    return {
        "status": "ok",
        "python_version": sys.version,
        "cwd": os.getcwd()
    }

@app.get("/")
def root():
    return {
        "service": "Research Agent API",
        "version": "1.0",
        "endpoints": {
            "/research": "POST - Run research query",
            "/health": "GET - Health check"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
