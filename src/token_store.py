import os
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Lazy Firebase init ──────────────────────────────────────────────────────
_db = None

def _get_db():
    global _db
    if _db is not None:
        return _db

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json")
        sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

        if not firebase_admin._apps:
            if os.path.exists(sa_file):
                cred = credentials.Certificate(sa_file)
            elif sa_json:
                import json, tempfile
                tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
                tmp.write(sa_json)
                tmp.close()
                cred = credentials.Certificate(tmp.name)
            else:
                logger.warning("No Firebase credentials found. Firestore features will be disabled.")
                return None
            firebase_admin.initialize_app(cred)

        _db = firestore.client()
        return _db
    except Exception as e:
        logger.error(f"Failed to initialize Firestore: {e}")
        return None

COLLECTION = "gmail_tokens"

def save_token(slack_user_id: str, creds) -> None:
    db = _get_db()
    if not db: return
    doc = {
        "access_token":  creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "scopes":        list(creds.scopes or []),
        "saved_at":      datetime.now(timezone.utc).isoformat(),
    }
    db.collection(COLLECTION).document(slack_user_id).set(doc)
    logger.info(f"[TokenStore] Saved token for Slack user {slack_user_id}")

def load_token(slack_user_id: str) -> Optional[object]:
    from google.oauth2.credentials import Credentials
    db = _get_db()
    if not db: return None
    try:
        doc = db.collection(COLLECTION).document(slack_user_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        return Credentials(
            token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            scopes=data.get("scopes", []),
        )
    except Exception:
        return None

def has_token(slack_user_id: str) -> bool:
    db = _get_db()
    if not db: return False
    try:
        doc = db.collection(COLLECTION).document(slack_user_id).get()
        return doc.exists
    except Exception:
        return False

# Export the db object for other modules
db = _get_db()