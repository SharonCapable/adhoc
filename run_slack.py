"""
Adhoc Research Bot — Slack v2 (Final)
======================================
Email flow: per-user Gmail OAuth → saves to user's own Gmail drafts.
No admin Domain-Wide Delegation needed. Works with personal GCP project.

How the email auth works (analogy):
  Old approach → bot is the postman, sends from one fixed address.
  New approach → bot is a secretary. Each person signs in once with Google,
                 the bot gets a key to their drafts folder only, and puts
                 the research there. The person reviews and sends themselves.

Env vars needed on Fly.io:
  ANTHROPIC_API_KEY, GEMINI_API_KEY, LLM_PROVIDER
  SLACK_BOT_TOKEN, SLACK_APP_TOKEN, SLACK_SIGNING_SECRET
  GOOGLE_SERVICE_ACCOUNT_JSON  (full contents of service-account .json)
  GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET
  GMAIL_REDIRECT_URI  (e.g. https://adhoc-research-bot.fly.dev/auth/gmail/callback)
"""

import os
import json
import random
import threading
import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from src.research_agent import ResearchAgent
from src.config import Config
from src.token_store import load_token, has_token, save_token, save_pending, get_pending

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App(token=Config.SLACK_BOT_TOKEN, signing_secret=Config.SLACK_SIGNING_SECRET)
research_agent = ResearchAgent(
    service_account_file=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service-account.json")
)

# Persistent Trivia Status using Firestore (with fallback to in-memory)
from src.token_store import db

def save_trivia_pass(user_id: str):
    if db:
        try:
            doc_ref = db.collection("trivia_status").document(user_id)
            doc_ref.set({"passed": True, "timestamp": "2026-05-01"})
        except Exception as e:
            logger.warning(f"Firestore save failed: {e}")

def check_trivia_pass(user_id: str) -> bool:
    if db:
        try:
            doc_ref = db.collection("trivia_status").document(user_id)
            doc = doc_ref.get()
            return doc.exists and doc.to_dict().get("passed", False)
        except Exception as e:
            logger.warning(f"Firestore read failed: {e}")
    return False

def delete_bot_messages(client, channel_id: str):
    """Deletes recent bot messages in the channel to clean up."""
    try:
        # Get recent messages
        result = client.conversations_history(channel=channel_id, limit=50)
        bot_user_id = client.auth_test()["user_id"]
        for msg in result["messages"]:
            if msg.get("user") == bot_user_id:
                client.chat_delete(channel=channel_id, ts=msg["ts"])
    except Exception as e:
        logger.error(f"Failed to clear messages: {e}")

BASE_URL = os.getenv(
    "GMAIL_REDIRECT_URI",
    "https://adhoc-research-bot.fly.dev/auth/gmail/callback"
).replace("/auth/gmail/callback", "")   # e.g. https://adhoc-research-bot.fly.dev


# ─────────────────────────────────────────────────────────────
# GMAIL — save to user's own drafts
# ─────────────────────────────────────────────────────────────

def save_to_gmail_draft(slack_user_id: str, query: str, summary: str,
                        to_addr: str = "", subject: str = None) -> str:
    """
    Save a research summary as a Gmail draft in the user's own account.
    Returns the Gmail draft ID. Raises ValueError("no_token") if not authorised.
    """
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request

    creds = load_token(slack_user_id)
    if creds is None:
        raise ValueError("no_token")

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_token(slack_user_id, creds)

    service = build("gmail", "v1", credentials=creds)

    subject_line = subject or f"[Adhoc Research] {query[:60]}"
    summary_html = summary.replace("\n", "<br>")
    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:800px;margin:0 auto;">
      <div style="background:#1A56A0;padding:24px;border-radius:8px 8px 0 0;">
        <h1 style="color:white;margin:0;font-size:22px;">🔬 Research Summary</h1>
        <p style="color:#A8CCF0;margin:8px 0 0;">Adhoc · AyaData AI Solutions</p>
      </div>
      <div style="background:#f4f6f9;padding:16px 24px;">
        <p style="margin:0;color:#555;"><strong>Research Query:</strong> {query}</p>
      </div>
      <div style="padding:24px;border:1px solid #ddd;border-top:none;line-height:1.7;color:#333;">
        {summary_html}
      </div>
      <div style="background:#f4f6f9;padding:16px 24px;border-radius:0 0 8px 8px;
                  border:1px solid #ddd;border-top:none;font-size:12px;color:#999;">
        Saved as draft by Adhoc Research Bot · Review and send at your discretion.
      </div>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject_line
    msg["To"]      = to_addr
    msg.attach(MIMEText(html_body, "html"))

    raw   = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()

    logger.info(f"[Gmail] Draft saved for Slack user {slack_user_id}: {draft['id']}")
    return draft["id"]


# ─────────────────────────────────────────────────────────────
# TRIVIA BANK
# ─────────────────────────────────────────────────────────────

TRIVIA_BANK = [
    {
        "question": "Which activation function is at the root of the 'dying neuron' problem?",
        "options": ["Sigmoid", "Tanh", "ReLU", "Softmax"],
        "answer": "C",
        "explanation": "ReLU outputs 0 for all negative inputs. Neurons stuck there stop learning — the 'dying ReLU' problem."
    },
    {
        "question": "What does RAG stand for in the context of LLMs?",
        "options": ["Retrieval-Augmented Generation", "Recursive Attention Graph", "Ranked Aggregation Gateway", "Residual Attention Gate"],
        "answer": "A",
        "explanation": "RAG = Retrieval-Augmented Generation. Grounds LLM responses with retrieved external documents."
    },
    {
        "question": "Which company published 'Attention Is All You Need' (2017)?",
        "options": ["OpenAI", "Meta AI", "Google Brain", "DeepMind"],
        "answer": "C",
        "explanation": "The Transformer paper came from Google Brain researchers in 2017."
    },
    {
        "question": "In MLOps, what does 'data drift' refer to?",
        "options": [
            "Data migrating between cloud regions",
            "Model weights shifting during training",
            "Changes in input data distribution over time",
            "Latency increase in data pipelines"
        ],
        "answer": "C",
        "explanation": "Data drift = statistical properties of model inputs change over time, degrading performance."
    },
    {
        "question": "Which metric measures the % of actual positives correctly identified?",
        "options": ["Precision", "Recall", "F1 Score", "Specificity"],
        "answer": "B",
        "explanation": "Recall = TP / (TP + FN). Of all actual positives, how many did we catch?"
    },
    {
        "question": "What is the primary purpose of a vector database in AI systems?",
        "options": [
            "Storing images as binary blobs",
            "Efficient similarity search over high-dimensional embeddings",
            "Running SQL queries on model outputs",
            "Caching LLM responses"
        ],
        "answer": "B",
        "explanation": "Vector DBs (Pinecone, Weaviate, Qdrant) index embeddings for fast nearest-neighbor similarity search."
    },
    {
        "question": "Which technique reduces model size by replacing 32-bit weights with lower precision?",
        "options": ["Dropout", "Quantization", "Pruning", "Distillation"],
        "answer": "B",
        "explanation": "Quantization converts weights to 8-bit or 4-bit integers, reducing memory and inference cost."
    },
    {
        "question": "In speech models, what does WER measure?",
        "options": ["Web Entity Rate", "Word Error Rate", "Weighted Encoding Ratio", "Waveform Error Ratio"],
        "answer": "B",
        "explanation": "WER = (Substitutions + Deletions + Insertions) / Total Words. Primary metric for ASR quality."
    },
    {
        "question": "Which architecture underpins most modern large language models?",
        "options": ["CNN", "RNN", "Decoder-only Transformer", "LSTM"],
        "answer": "C",
        "explanation": "GPT, Claude, Gemini, and Llama are all decoder-only Transformers using autoregressive generation."
    },
    {
        "question": "What does LoRA stand for in LLM fine-tuning?",
        "options": [
            "Loss-Optimised Regularisation Algorithm",
            "Low-Rank Adaptation",
            "Layered Output Retraining Architecture",
            "Learned Offset Retrieval Attention"
        ],
        "answer": "B",
        "explanation": "LoRA injects trainable low-rank matrices into attention layers — far fewer parameters than full fine-tuning."
    },
]

# ─────────────────────────────────────────────────────────────
# IN-MEMORY STATE
# ─────────────────────────────────────────────────────────────

trivia_state:    dict = {}   # user_id → { question, attempts, passed }
pending_research: dict = {}  # in-memory cache; Firestore is the persistent backing store


def store_pending(key: str, data: dict):
    pending_research[key] = data
    save_pending(key, data)


def fetch_pending(key: str) -> dict | None:
    if key in pending_research:
        return pending_research[key]
    data = get_pending(key)
    if data:
        pending_research[key] = data   # warm the cache
    return data


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

_GREETINGS = {"hello", "hi", "hey", "howdy", "hiya", "sup", "yo", "greetings",
               "good morning", "good afternoon", "good evening", "good day"}

def is_greeting(text: str) -> bool:
    import re as _re
    clean = _re.sub(r"[^\w\s]", "", text.lower()).strip()
    return clean in _GREETINGS


def has_passed_trivia(user_id: str) -> bool:
    # Check in-memory first, then Firestore
    if trivia_state.get(user_id, {}).get("passed"):
        return True
    if check_trivia_pass(user_id):
        trivia_state[user_id] = {"passed": True}
        return True
    return False


def send_trivia(client, channel: str, user_id: str):
    q = random.choice(TRIVIA_BANK)
    trivia_state[user_id] = {"question": q, "attempts": 0, "passed": False}
    client.chat_postMessage(
        channel=channel,
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f":brain: *Welcome to Adhoc Research Bot!*\n\n"
                        f"Answer a quick AI trivia question to get in.\n"
                        f"You have *3 attempts*.\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"*{q['question']}*"
                    )
                }
            },
            {
                "type": "actions",
                "block_id": f"trivia_{user_id}",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": f"{chr(65+i)}. {opt}"},
                        "value": chr(65 + i),
                        "action_id": f"trivia_answer_{chr(65+i)}"
                    }
                    for i, opt in enumerate(q["options"])
                ]
            }
        ],
        text=f"Trivia: {q['question']}"
    )


def research_blocks(query: str, findings: str, action_key: str) -> list:
    preview = (findings[:600] + ("..." if len(findings) > 600 else "")) or "_No findings were generated._"
    return [
        {"type": "header",
         "text": {"type": "plain_text", "text": "🔬 Research Complete", "emoji": True}},
        {"type": "section",
         "text": {"type": "mrkdwn", "text": f"*Query:* {query}"}},
        {"type": "divider"},
        {"type": "section",
         "text": {"type": "mrkdwn", "text": preview}},
        {"type": "divider"},
        {"type": "section",
         "text": {"type": "mrkdwn", "text": "*What would you like to do with these findings?*"}},
        {
            "type": "actions",
            "block_id": f"post_research_{action_key}",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📧 Construct Gmail Draft", "emoji": True},
                    "style": "primary",
                    "value": action_key,
                    "action_id": "action_construct_draft"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📄 Download as Doc", "emoji": True},
                    "value": action_key,
                    "action_id": "action_download_doc"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "📝 Download as MD", "emoji": True},
                    "value": action_key,
                    "action_id": "action_download_md"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🔁 Follow-up Query", "emoji": True},
                    "value": action_key,
                    "action_id": "action_followup"
                },
            ]
        }
    ]


def gmail_signin_blocks(action_key: str, slack_user_id: str) -> list:
    """Ephemeral message prompting user to connect their Gmail."""
    auth_url = f"{BASE_URL}/auth/gmail/start?slack_user_id={slack_user_id}"
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    ":email: *Save to Gmail Draft*\n\n"
                    "You haven't connected your Gmail yet. "
                    "Click below to sign in with Google — the bot only gets access "
                    "to create drafts, nothing else. You sign in once and it remembers you."
                )
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "🔗 Sign in with Google", "emoji": True},
                    "style": "primary",
                    "url": auth_url,
                    "action_id": "gmail_signin_link"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "✅ I've signed in — save draft now", "emoji": True},
                    "value": action_key,
                    "action_id": "gmail_save_after_auth"
                }
            ]
        }
    ]


# ─────────────────────────────────────────────────────────────
# TRIVIA HANDLERS
# ─────────────────────────────────────────────────────────────

import re

@app.action(re.compile("trivia_answer_.*"))
def handle_trivia_answer(ack, body, client):
    ack()
    user_id    = body["user"]["id"]
    channel    = body["channel"]["id"]
    chosen     = body["actions"][0]["value"]
    message_ts = body["message"]["ts"]

    state = trivia_state.get(user_id)
    if not state:
        client.chat_postEphemeral(channel=channel, user=user_id,
                                   text="Session expired. Mention me again.")
        return
    if state.get("passed"):
        client.chat_postEphemeral(channel=channel, user=user_id,
                                   text="Already passed! Ask your research question.")
        return

    state["attempts"] += 1
    correct     = state["question"]["answer"]
    explanation = state["question"]["explanation"]

    if chosen == correct:
        state["passed"] = True
        trivia_state[user_id] = state
        save_trivia_pass(user_id)  # Persist to Firestore
        client.chat_update(
            channel=channel, ts=message_ts,
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": (
                f":white_check_mark: *Correct!* Option {correct}.\n\n_{explanation}_\n\n"
                f":rocket: *Access granted.* You are now cleared for all future sessions.\n"
                f"Try asking me anything now!"
            )}}],
            text="Correct! Access granted."
        )
    elif state["attempts"] >= 3:
        trivia_state.pop(user_id, None)
        client.chat_update(
            channel=channel, ts=message_ts,
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": (
                f":x: Wrong again. Answer was *{correct}*.\n_{explanation}_\n\n"
                f"Here's a fresh question :nerd_face:"
            )}}],
            text="Wrong. New question coming."
        )
        send_trivia(client, channel, user_id)
    else:
        remaining = 3 - state["attempts"]
        client.chat_postEphemeral(
            channel=channel, user=user_id,
            text=f":x: Not quite. *{remaining}* attempt{'s' if remaining > 1 else ''} left."
        )


# ─────────────────────────────────────────────────────────────
# MENTION HANDLER
# ─────────────────────────────────────────────────────────────

@app.event("app_mention")
def handle_mention(event, say, client):
    user_id = event["user"]
    channel = event["channel"]
    query   = event["text"].split(">", 1)[-1].strip()

    if "clear" in query.lower():
        say(text=f":broom: Cleaning up my messages in this channel...")
        threading.Thread(target=delete_bot_messages, args=(client, channel), daemon=True).start()
        return

    # Check for Identity / General Questions
    identity_triggers = ["who are you", "what can you do", "help", "how does this work", "about yourself"]
    if any(trigger in query.lower() for trigger in identity_triggers):
        from src.llm_provider import get_llm_provider
        llm = get_llm_provider()
        identity_prompt = f"You are Adhoc Research Bot v2, a premium AI research agent developed for AyaData AI Solutions. You conduct deep web research using Gemini 2.5 and save findings to Gmail Drafts. Answer this user's question about you politely: {query}"
        response = llm.generate(identity_prompt)
        say(text=response)
        return

    if not has_passed_trivia(user_id):
        say(text=f"<@{user_id}> Trivia gate first! :brain:")
        send_trivia(client, channel, user_id)
        return

    if is_greeting(query):
        say(text=f"Hello <@{user_id}>! :wave: You're all set — just ask me a research question.")
        return

    # Post initial message and handle the rest in a THREAD to avoid channel noise
    ack_msg = client.chat_postMessage(
        channel=channel,
        text=f":hourglass_flowing_sand: Researching *{query}*... Check the thread for progress."
    )
    thread_ts = ack_msg["ts"]

    def do_research():
        try:
            client.chat_postMessage(channel=channel, thread_ts=thread_ts,
                                    text="🔍 Connecting to Gemini 2.5 + Google Search Index...")

            result   = research_agent.run(query)
            findings = result.get("research_findings", "")
            status   = result.get("status", "")
            success  = bool(findings) and not findings.startswith("Error during analysis:")

            if success:
                key = f"{user_id}_{thread_ts}"
                store_pending(key, {
                    "findings":    findings,
                    "query":       query,
                    "channel":     channel,
                    "output_path": result.get("output_path", ""),
                    "user_id":     user_id,
                })
                client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    blocks=research_blocks(query, findings, key),
                    text=f"Research complete: {query}"
                )
            else:
                detail = findings or f"Status: {status}"
                client.chat_postMessage(
                    channel=channel,
                    thread_ts=thread_ts,
                    text=f":x: *Research failed for:* _{query}_\n\n`{detail[:400]}`"
                )
        except Exception as e:
            logger.error(f"Research error: {e}", exc_info=True)
            client.chat_postMessage(channel=channel, thread_ts=thread_ts,
                                    text=f":x: Research failed: `{str(e)[:200]}`")

    threading.Thread(target=do_research, daemon=True).start()


# ─────────────────────────────────────────────────────────────
# GMAIL DRAFT — modal-based construct + save flow
# ─────────────────────────────────────────────────────────────

def _open_draft_modal(client, trigger_id: str, action_key: str, data: dict):
    """Open the Slack modal so the user can preview/edit before saving to Gmail."""
    query   = data.get("query", "")
    preview = data.get("findings", "")[:2000]
    client.views_open(
        trigger_id=trigger_id,
        view={
            "type": "modal",
            "callback_id": f"gmail_draft_modal_{action_key}",
            "title": {"type": "plain_text", "text": "Construct Gmail Draft"},
            "submit": {"type": "plain_text", "text": "Save to Drafts"},
            "close":  {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {
                    "type": "section",
                    "text": {"type": "mrkdwn",
                             "text": f"_Research:_ *{query[:80]}*\n\nEdit the fields below, then click *Save to Drafts*."}
                },
                {
                    "type": "input", "block_id": "to_block", "optional": True,
                    "label": {"type": "plain_text", "text": "To (optional — fill in Gmail before sending)"},
                    "element": {"type": "plain_text_input", "action_id": "to_input",
                                "placeholder": {"type": "plain_text", "text": "colleague@example.com"}}
                },
                {
                    "type": "input", "block_id": "subject_block",
                    "label": {"type": "plain_text", "text": "Subject"},
                    "element": {"type": "plain_text_input", "action_id": "subject_input",
                                "initial_value": f"[Adhoc Research] {query[:60]}"}
                },
                {
                    "type": "input", "block_id": "summary_block",
                    "label": {"type": "plain_text", "text": "Summary (edit before saving)"},
                    "element": {"type": "plain_text_input", "action_id": "summary_input",
                                "multiline": True, "initial_value": preview}
                },
            ]
        }
    )


@app.action("action_construct_draft")
def handle_construct_draft(ack, body, client):
    ack()
    action_key = body["actions"][0]["value"]
    data       = fetch_pending(action_key)
    channel    = body["channel"]["id"]
    user_id    = body["user"]["id"]

    if not data:
        client.chat_postEphemeral(channel=channel, user=user_id,
                                   text=":warning: Session expired. Re-run your query.")
        return

    if has_token(user_id):
        _open_draft_modal(client, body["trigger_id"], action_key, data)
    else:
        client.chat_postEphemeral(
            channel=channel, user=user_id,
            blocks=gmail_signin_blocks(action_key, user_id),
            text="Connect your Gmail to save research as a draft."
        )


@app.action("gmail_save_after_auth")
def handle_save_after_auth(ack, body, client):
    """User clicked 'I've signed in' after OAuth — open modal if token is now present."""
    ack()
    action_key = body["actions"][0]["value"]
    data       = fetch_pending(action_key)
    channel    = body["channel"]["id"]
    user_id    = body["user"]["id"]

    if not data:
        client.chat_postEphemeral(channel=channel, user=user_id,
                                   text=":warning: Session expired. Re-run your query.")
        return

    if has_token(user_id):
        _open_draft_modal(client, body["trigger_id"], action_key, data)
    else:
        client.chat_postEphemeral(
            channel=channel, user=user_id,
            text=":x: Couldn't find your Gmail auth. Make sure you completed sign-in in the browser tab."
        )


@app.action("gmail_signin_link")
def handle_signin_link(ack, **_):
    ack()


@app.view(re.compile("gmail_draft_modal_.*"))
def handle_gmail_draft_submit(ack, body, client):
    ack()
    action_key = body["view"]["callback_id"].replace("gmail_draft_modal_", "")
    values     = body["view"]["state"]["values"]
    user_id    = body["user"]["id"]

    to_addr = (values.get("to_block", {}).get("to_input", {}).get("value") or "").strip()
    subject = values["subject_block"]["subject_input"]["value"]
    summary = values["summary_block"]["summary_input"]["value"]

    data    = fetch_pending(action_key)
    channel = data.get("channel") if data else None

    try:
        save_to_gmail_draft(
            slack_user_id=user_id,
            query=data["query"] if data else "",
            summary=summary,
            to_addr=to_addr,
            subject=subject,
        )
        if channel:
            client.chat_postMessage(
                channel=channel,
                text=(
                    f":white_check_mark: <@{user_id}> Draft saved to *Gmail Drafts*.\n"
                    f"Open Gmail → Drafts → _{subject[:60]}_ → add recipients and send."
                )
            )
    except ValueError as e:
        if "no_token" in str(e) and channel:
            client.chat_postEphemeral(channel=channel, user=user_id,
                                       text=":x: Gmail session expired. Click the button again to reconnect.")
    except Exception as e:
        logger.error(f"Draft save failed: {e}", exc_info=True)
        if channel:
            client.chat_postEphemeral(channel=channel, user=user_id,
                                       text=f":x: Draft save failed: `{str(e)[:200]}`")


# ─────────────────────────────────────────────────────────────
# DOWNLOAD ACTIONS
# ─────────────────────────────────────────────────────────────

@app.action("action_download_doc")
def handle_download_doc(ack, body, client):
    ack()
    action_key = body["actions"][0]["value"]
    data       = fetch_pending(action_key)
    channel    = body["channel"]["id"]
    user_id    = body["user"]["id"]
    if not data:
        client.chat_postEphemeral(channel=channel, user=user_id, text=":warning: Session expired.")
        return
    content  = f"# Research Report\n\n**Query:** {data['query']}\n\n---\n\n{data['findings']}"
    filename = f"research_{data['query'][:30].replace(' ','_')}.md"
    client.files_upload_v2(
        channel=channel, content=content, filename=filename,
        title=f"Research: {data['query'][:50]}",
        initial_comment=":page_facing_up: Research as a formatted document."
    )


@app.action("action_download_md")
def handle_download_md(ack, body, client):
    ack()
    action_key = body["actions"][0]["value"]
    data       = fetch_pending(action_key)
    channel    = body["channel"]["id"]
    user_id    = body["user"]["id"]
    if not data:
        client.chat_postEphemeral(channel=channel, user=user_id, text=":warning: Session expired.")
        return
    content  = f"# Research Report\n\n**Query:** {data['query']}\n\n---\n\n{data['findings']}"
    filename = f"research_{data['query'][:30].replace(' ','_')}.md"
    client.files_upload_v2(
        channel=channel, content=content, filename=filename,
        title=f"Research: {data['query'][:50]}",
        initial_comment=":memo: Raw Markdown — ready for GitHub, Notion, or docs."
    )


# ─────────────────────────────────────────────────────────────
# FOLLOW-UP QUERY
# ─────────────────────────────────────────────────────────────

@app.action("action_followup")
def handle_followup(ack, body, client):
    ack()
    action_key = body["actions"][0]["value"]
    data       = fetch_pending(action_key) or {}
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": f"followup_modal_{action_key}",
            "title": {"type": "plain_text", "text": "Follow-up Research"},
            "submit": {"type": "plain_text", "text": "Research"},
            "close":  {"type": "plain_text", "text": "Cancel"},
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn",
                  "text": f"_Building on:_ *{data.get('query','previous research')}*"}},
                {"type": "input", "block_id": "followup_block",
                 "label": {"type": "plain_text", "text": "Your follow-up question"},
                 "element": {"type": "plain_text_input", "action_id": "followup_input",
                   "placeholder": {"type": "plain_text",
                     "text": "e.g. Dive deeper into productionisation options"}}}
            ]
        }
    )


@app.view(re.compile("followup_modal_.*"))
def handle_followup_submit(ack, body, client):
    ack()
    action_key = body["view"]["callback_id"].replace("followup_modal_", "")
    original   = pending_research.get(action_key, {})
    followup_q = body["view"]["state"]["values"]["followup_block"]["followup_input"]["value"]
    user_id    = body["user"]["id"]
    channel    = original.get("channel")
    if not channel:
        return

    combined = (
        f"{followup_q}\n\n[Context from previous research on "
        f"'{original.get('query','')}': {original.get('findings','')[:800]}...]"
    )
    client.chat_postMessage(channel=channel,
                            text=f":hourglass_flowing_sand: Follow-up: *{followup_q}*")

    def do_followup():
        try:
            result   = research_agent.run(combined)
            findings = result.get("research_findings", "No findings.")
            new_key  = f"{user_id}_followup_{action_key}"
            store_pending(new_key, {
                "findings": findings, "query": followup_q,
                "channel": channel, "user_id": user_id,
                "output_path": result.get("output_path", ""),
            })
            client.chat_postMessage(
                channel=channel,
                blocks=research_blocks(followup_q, findings, new_key),
                text=f"Follow-up complete: {followup_q}"
            )
        except Exception as e:
            client.chat_postMessage(channel=channel,
                                    text=f":x: Follow-up failed: `{str(e)[:200]}`")

    threading.Thread(target=do_followup, daemon=True).start()


# ─────────────────────────────────────────────────────────────
# CATCH-ALL + ENTRYPOINT
# ─────────────────────────────────────────────────────────────

@app.event("message")
def handle_message(body, logger):
    # Log the message type to the terminal to confirm connectivity
    print(f"DEBUG: Received event: {body.get('event', {}).get('type')}")
    logger.debug(body)


def main():
    print("╔══════════════════════════════════════════════╗")
    print("║  Adhoc Research Bot v2  —  Slack Mode        ║")
    print("╠══════════════════════════════════════════════╣")
    print("║  ✅ Trivia gate (10 AI/ML questions)          ║")
    print("║  ✅ Per-user Gmail OAuth → saves to Drafts    ║")
    print("║  ✅ Block Kit post-research actions           ║")
    print("║  ✅ Background research threading             ║")
    print("╚══════════════════════════════════════════════╝\n")
    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    handler.start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped.")
    except Exception as e:
        print(f"\n❌ Startup error: {e}")