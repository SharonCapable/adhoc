# 🔬 Research Agent with LangGraph

An intelligent research agent that fetches context from Google Drive and conducts web research using Claude AI.

## 🏗️ Architecture

```
┌─────────────┐
│   Trigger   │  (CLI or Slack)
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│       LangGraph Agent               │
│  ┌──────────────────────────────┐   │
│  │ 1. Fetch Framework (Drive)   │   │
│  └──────────────────────────────┘   │
│             ▼                        │
│  ┌──────────────────────────────┐   │
│  │ 2. Search Web (Claude)       │   │
│  └──────────────────────────────┘   │
│             ▼                        │
│  ┌──────────────────────────────┐   │
│  │ 3. Fetch Content (URLs)      │   │
│  └──────────────────────────────┘   │
│             ▼                        │
│  ┌──────────────────────────────┐   │
│  │ 4. Analyze (Claude)          │   │
│  └──────────────────────────────┘   │
│             ▼                        │
│  ┌──────────────────────────────┐   │
│  │ 5. Save Output (JSON/MD)     │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

## 📋 Prerequisites

1. **Python 3.10+**
2. **Claude API Key** (from Anthropic)
3. **Google Cloud Account** (for Drive API)
4. **Slack Workspace** (optional, for Slack trigger)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Create project directory
mkdir adhoc-research
cd adhoc-research

# Create virtual environment
python -m venv adhoc
source adhoc/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy template
cp .env.template .env

# Edit .env and add your API keys
nano .env  # or use your favorite editor
```

**Required in .env:**
```
ANTHROPIC_API_KEY=your_claude_api_key
GOOGLE_CREDENTIALS_PATH=credentials.json
```

### 3. Setup Google Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select existing)
3. Enable **Google Drive API**
4. Create **OAuth 2.0 credentials** (Desktop app)
5. Download credentials and save as `credentials.json` in project root

### 4. Create Output Directory

```bash
mkdir -p data/outputs
```

### 5. Test the Agent

**Option A: CLI Mode (Terminal)**

```bash
python run_cli.py
```

Then enter your research query when prompted:
```
🔍 Enter your research query: what are the latest AI trends in education?
```

**Option B: Slack Mode**

First, setup your Slack bot:

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Create New App → From Scratch
3. Add **Bot Token Scopes**:
   - `chat:write`
   - `app_mentions:read`
   - `im:history`
   - `im:read`
4. Enable **Socket Mode** (get App-Level Token)
5. Install app to workspace
6. Copy tokens to `.env`:
   ```
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_APP_TOKEN=xapp-...
   ```

Then run:
```bash
python run_slack.py
```

In Slack, mention the bot:
```
@ResearchBot what are the latest AI trends in education?
```

Or DM the bot:
```
research AI trends in education
```

## 📁 Project Structure

```
research-agent/
├── .env                    # Your API keys (DO NOT COMMIT)
├── .env.template          # Template for environment variables
├── .gitignore            # Git ignore rules
├── requirements.txt      # Python dependencies
├── README.md            # This file
│
├── run_cli.py           # Option A: Terminal trigger
├── run_slack.py         # Option B: Slack trigger
│
├── src/
│   ├── config.py              # Configuration management
│   ├── agent_state.py         # State definition for LangGraph
│   ├── research_agent.py      # Main LangGraph agent
│   ├── google_drive_tool.py   # Google Drive integration
│   └── research_tools.py      # Web search & fetch tools
│
└── data/
    └── outputs/              # Research results saved here
        ├── research_*.json   # JSON format
        └── research_*.md     # Markdown format
```

## 🔧 How It Works

### The Flow (LangGraph)

The agent follows a sequential workflow:

1. **Fetch Framework** → Loads research guidelines from Google Drive
2. **Search Web** → Uses Claude to search for relevant sources
3. **Fetch Content** → Downloads full content from URLs
4. **Analyze** → Claude synthesizes findings based on framework
5. **Save Output** → Stores results as JSON and Markdown

### State Management

Each node in the graph reads from and writes to a shared `ResearchState`:

```python
{
  "research_query": "...",
  "framework_content": "...",
  "search_results": [...],
  "sources_with_content": [...],
  "research_findings": "...",
  "output_path": "..."
}
```

## 🎯 Usage Examples

### CLI Mode

```bash
python run_cli.py
```

```
🔍 Enter your research query: market analysis for sourcing products in Ghana
```

The agent will:
1. Load your research framework from Google Drive
2. Search for relevant sources
3. Fetch and analyze content
4. Save results to `data/outputs/`

### Slack Mode

```bash
python run_slack.py
```

In Slack:
```
@ResearchBot analyze the current state of renewable energy in West Africa
```

Bot will:
- Acknowledge your request
- Run the research pipeline
- Reply with findings in the thread

## 📤 Output Format

### JSON Output (`research_TIMESTAMP.json`)

```json
{
  "research_query": "...",
  "timestamp": "20241012_143022",
  "framework_used": true,
  "sources": [
    {
      "title": "...",
      "url": "...",
      "content": "..."
    }
  ],
  "findings": "..."
}
```

### Markdown Output (`research_TIMESTAMP.md`)

```markdown
# Research Report

**Query:** Your research question

**Date:** 2024-10-12 14:30:22

---

[Analysis and findings here...]

---

## Sources

1. [Source Title](url)
2. [Source Title](url)
```

## 🔐 Security Notes

- **.env file** contains sensitive API keys → **NEVER commit to git**
- **credentials.json** is your Google OAuth credentials → **NEVER commit to git**
- **token.json** stores OAuth tokens → **NEVER commit to git**
- All these are in `.gitignore` by default

## 🐛 Troubleshooting

### "ANTHROPIC_API_KEY not found"
- Make sure `.env` file exists with your API key
- Check that you copied `.env.template` to `.env`

### "Google credentials not found"
- Download OAuth credentials from Google Cloud Console
- Save as `credentials.json` in project root

### "No module named 'langchain'"
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt`

### Slack bot not responding
- Check bot is installed to workspace
- Verify tokens in `.env`
- Make sure Socket Mode is enabled
- Bot needs to be mentioned or in DM

## 📝 Customization

### Change Research Depth

Edit `src/config.py`:
```python
MAX_SEARCH_RESULTS = 10  # Increase for more sources
MAX_CONTENT_LENGTH = 5000  # Increase for longer extracts
```

### Modify Research Framework

1. Update your Google Drive document
2. Agent will fetch latest version on next run

### Add Custom Analysis

Edit `src/research_tools.py` → `analyze_sources()` method to customize how Claude analyzes sources.

## 🤝 Contributing

When pushing to GitHub:
1. Ensure `.env` is in `.gitignore`
2. Remove any sensitive data
3. Test with fresh clone

## 📄 License

MIT License - feel free to use and modify!

---

**Built with:**
- [LangChain](https://langchain.com) - LLM framework
- [LangGraph](https://langchain.com/langgraph) - Agent orchestration
- [Claude](https://anthropic.com) - AI research & analysis
- [Slack Bolt](https://slack.dev/bolt-python/) - Slack integration