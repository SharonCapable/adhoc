"""
api_server.py — v2
==================
FastAPI server with:
  - /research  POST  — research pipeline
  - /health    GET   — health check
  - /auth/gmail/callback  GET  — Gmail OAuth callback (saves token to Firestore)
  - /auth/gmail/start     GET  — redirects user to Google consent screen
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional
import sys, os, json, subprocess, traceback, logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── OAuth config ────────────────────────────────────────────────────────────
GMAIL_SCOPES    = ["https://www.googleapis.com/auth/gmail.drafts"]
CLIENT_ID       = os.getenv("GMAIL_CLIENT_ID", "")
CLIENT_SECRET   = os.getenv("GMAIL_CLIENT_SECRET", "")
# Must match exactly what you set in GCP OAuth credentials → Authorised redirect URIs
# e.g. https://adhoc-research-bot.fly.dev/auth/gmail/callback
REDIRECT_URI    = os.getenv(
    "GMAIL_REDIRECT_URI",
    "https://adhoc-research-bot.fly.dev/auth/gmail/callback"
)

# ── Research endpoint ───────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    query: str
    frameworkSource: Optional[str] = None


@app.post("/research")
async def run_research(request: ResearchRequest):
    logger.info(f"Research request: {request.query[:50]}...")
    try:
        input_data = json.dumps({
            "query": request.query,
            "frameworkSource": request.frameworkSource
        })
        process = subprocess.Popen(
            [sys.executable, "run_api.py"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        stdout, stderr = process.communicate(input=input_data, timeout=120)
        if stderr:
            logger.warning(f"Subprocess stderr: {stderr}")
        if process.returncode != 0:
            raise HTTPException(status_code=500, detail={
                "error": "Script failed", "stderr": stderr, "stdout": stdout[:500]
            })
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as e:
            return {"success": False, "error": "Invalid JSON output", "raw": stdout[:500]}
    except subprocess.TimeoutExpired:
        process.kill()
        raise HTTPException(status_code=504, detail="Timed out after 120s")
    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail={"error": str(e)})


# ── Gmail OAuth — Step 1: redirect user to Google consent screen ─────────────

@app.get("/auth/gmail/start")
async def gmail_auth_start(request: Request):
    """
    The Slack bot sends users here when they click 'Sign in with Google'.
    We embed the Slack user_id in the OAuth state param so we know who
    to store the token for when they come back.

    slack_user_id is passed as a query param:
      GET /auth/gmail/start?slack_user_id=U012AB3CD
    """
    from google_auth_oauthlib.flow import Flow

    slack_user_id = request.query_params.get("slack_user_id", "unknown")

    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id":     CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                "token_uri":     "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=GMAIL_SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    # state carries the Slack user_id through the OAuth round-trip
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",          # force consent so we always get a refresh_token
        state=slack_user_id,       # comes back in the callback
    )

    return RedirectResponse(url=auth_url)


# ── Gmail OAuth — Step 2: Google redirects back here after consent ──────────

@app.get("/auth/gmail/callback")
async def gmail_auth_callback(request: Request):
    """
    Google redirects here after the user approves Gmail Drafts access.
    We exchange the auth code for tokens and save them to Firestore,
    keyed by the Slack user_id we embedded in state.

    On success → show a friendly 'you can close this tab' page.
    """
    from google_auth_oauthlib.flow import Flow
    from src.token_store import save_token

    code           = request.query_params.get("code")
    slack_user_id  = request.query_params.get("state", "unknown")
    error          = request.query_params.get("error")

    if error:
        logger.warning(f"OAuth error for {slack_user_id}: {error}")
        return HTMLResponse(_html_page(
            "❌ Authorisation cancelled",
            "You cancelled Google sign-in. Go back to Slack and try again.",
            success=False
        ))

    if not code:
        return HTMLResponse(_html_page(
            "❌ Missing auth code",
            "Something went wrong. Please try again from Slack.",
            success=False
        ))

    try:
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id":     CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                    "token_uri":     "https://oauth2.googleapis.com/token",
                    "redirect_uris": [REDIRECT_URI],
                }
            },
            scopes=GMAIL_SCOPES,
            redirect_uri=REDIRECT_URI,
            state=slack_user_id,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials

        save_token(slack_user_id, creds)
        logger.info(f"[OAuth] Token saved for Slack user {slack_user_id}")

        return HTMLResponse(_html_page(
            "✅ Gmail connected!",
            "You can close this tab and return to Slack. "
            "The bot will now save research findings to your Gmail drafts.",
            success=True
        ))

    except Exception as e:
        logger.error(f"[OAuth callback error] {e}", exc_info=True)
        return HTMLResponse(_html_page(
            "❌ Something went wrong",
            f"Error: {str(e)[:200]}. Please try again from Slack.",
            success=False
        ))


def _html_page(title: str, message: str, success: bool = True) -> str:
    colour = "#1A56A0" if success else "#C0392B"
    icon   = "✅" if success else "❌"
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>{title}</title>
      <style>
        body {{ font-family: Arial, sans-serif; display: flex; justify-content: center;
               align-items: center; height: 100vh; margin: 0; background: #f4f6f9; }}
        .card {{ background: white; border-radius: 12px; padding: 48px 40px;
                 box-shadow: 0 4px 24px rgba(0,0,0,0.08); max-width: 440px; text-align: center; }}
        .icon {{ font-size: 48px; margin-bottom: 16px; }}
        h1 {{ color: {colour}; font-size: 22px; margin: 0 0 12px; }}
        p  {{ color: #555; line-height: 1.6; margin: 0; }}
        .brand {{ color: #999; font-size: 12px; margin-top: 32px; }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="icon">{icon}</div>
        <h1>{title}</h1>
        <p>{message}</p>
        <p class="brand">Adhoc Research Bot · AyaData AI Solutions</p>
      </div>
    </body>
    </html>
    """


# ── Health / root ────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "python_version": sys.version, "cwd": os.getcwd()}


@app.get("/")
def root():
    return {
        "service": "Adhoc Research Agent API",
        "version": "2.0",
        "endpoints": {
            "/research":              "POST — run research query",
            "/health":                "GET  — health check",
            "/auth/gmail/start":      "GET  — begin Gmail OAuth (?slack_user_id=...)",
            "/auth/gmail/callback":   "GET  — OAuth redirect target (set in GCP)",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))