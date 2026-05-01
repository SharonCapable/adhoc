"""
src/token_store.py
==================
Stores and retrieves per-user Gmail OAuth tokens in Firebase Firestore.

Think of Firestore here like a safety deposit box at a bank:
  - Each Slack user_id is a unique box number
  - Their OAuth token is the contents of the box
  - Only the bot (with the service account key) can open any box
  - When a user reauthorises, their box contents are simply replaced

Collection structure in Firestore:
  gmail_tokens/
    {slack_user_id}/
      access_token:  str
      refresh_token: str
      token_uri:     str
      client_id:     str
      client_secret: str
      scopes:        list[str]
      saved_at:      timestamp
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Lazy Firebase init ──────────────────────────────────────────────────────
_db = None

def _get_db():
    """
    Initialise Firestore client once, reuse after.
    Uses the same service account JSON already in your env —
    no separate Firebase credential needed.
    """
    global _db
    if _db is not None:
        return _db

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
            raise RuntimeError(
                "No Firebase credentials found. "
                "Set GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON."
            )
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    return _db


COLLECTION = "gmail_tokens"


def save_token(slack_user_id: str, creds) -> None:
    """
    Persist a user's Google OAuth credentials to Firestore.

    Args:
        slack_user_id: The Slack user ID (e.g. "U012AB3CD")
        creds: google.oauth2.credentials.Credentials object
    """
    db = _get_db()
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
    """
    Load a user's stored credentials from Firestore.

    Returns:
        google.oauth2.credentials.Credentials if found, else None
    """
    from google.oauth2.credentials import Credentials

    db = _get_db()
    doc = db.collection(COLLECTION).document(slack_user_id).get()

    if not doc.exists:
        return None

    data = doc.to_dict()
    creds = Credentials(
        token=data.get("access_token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes", []),
    )
    logger.info(f"[TokenStore] Loaded token for Slack user {slack_user_id}")
    return creds


def delete_token(slack_user_id: str) -> None:
    """Remove a user's stored credentials (e.g. on explicit sign-out)."""
    db = _get_db()
    db.collection(COLLECTION).document(slack_user_id).delete()
    logger.info(f"[TokenStore] Deleted token for Slack user {slack_user_id}")


def has_token(slack_user_id: str) -> bool:
    """Quick check — does this user have stored credentials?"""
    db = _get_db()
    doc = db.collection(COLLECTION).document(slack_user_id).get()
    return doc.exists