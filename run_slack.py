"""
Slack Bot Trigger for Research Agent (Option B)

This bot listens for messages in Slack and triggers research.
"""
import os
from slack_bolt import App
import logging
from slack_bolt.adapter.socket_mode import SocketModeHandler
from src.research_agent import ResearchAgent
from src.config import Config

logging.basicConfig(level=logging.DEBUG)

# Initialize Slack app with proper token configuration
app = App(
    token=Config.SLACK_BOT_TOKEN,
    signing_secret=Config.SLACK_SIGNING_SECRET
)

# Initialize research agent (singleton)
research_agent = ResearchAgent()

# raw event logger
@app.event("*")
def log_all_events(body, logger, event, say):
    logger.debug("Received event: %s", body)

@app.event("app_mention")
def handle_mention(event, say, logger):
    """
    Handle when someone mentions the bot.
    Example: @ResearchBot what are the latest trends in AI education?
    """
    user = event['user']
    text = event['text']
    channel = event['channel']
    
    # Remove bot mention from text to get the actual query
    query = text.split('>', 1)[-1].strip()
    
    if not query:
        say(
            text=f"Hey <@{user}>! 👋 Ask me to research something!\n"
                 f"Example: `@ResearchBot what are the latest trends in AI education?`",
            channel=channel
        )
        return
    
    # Acknowledge the request
    say(
        text=f"🔍 Researching: *{query}*",
        channel=channel
    )
    
    try:
        # Run research
        result = research_agent.run(query)
        
        # Extract output path from result
        output_file = result.get("output_path") or result.get("output", "")
        
        # Load and parse the JSON output
        findings = "No findings available"
        sources_text = ""
        
        if output_file and os.path.exists(output_file):
            import json
            with open(output_file, 'r', encoding='utf-8') as f:
                research_data = json.load(f)
            
            # Extract key findings and sources
            # Try both possible locations for findings
            findings = research_data.get("findings") or research_data.get("analysis", {}).get("findings", "No findings available")
            sources = research_data.get("sources", [])
            
            # Truncate findings if too long for Slack (3000 char limit)
            if len(findings) > 1500:
                findings = findings[:1500] + "...\n\n_See full report for complete findings._"
            
            # Format sources for Slack (clickable links)
            if sources:
                sources_text = "\n\n📚 *Sources:*\n"
                for i, source in enumerate(sources[:5], 1):  # Limit to 5 sources
                    title = source.get('title', 'Untitled')
                    url = source.get('url', '')
                    if url:
                        sources_text += f"{i}. <{url}|{title}>\n"
                    else:
                        sources_text += f"{i}. {title}\n"
        
        # Send response
        say(
            text=f"✅ *Research Complete*\n\n{findings}{sources_text}",
            channel=channel
        )
        
    except Exception as e:
        logger.error(f"Error during research: {e}", exc_info=True)
        say(
            text=f"❌ Sorry <@{user}>, something went wrong during research.\nError: {str(e)[:200]}",
            channel=channel
        )


@app.message("research")
def handle_research_keyword(message, say, logger):
    """
    Handle direct messages containing 'research'.
    This works in DMs with the bot.
    """
    text = message.get('text', '')
    user = message['user']
    
    # Extract query (everything after 'research')
    if 'research' in text.lower():
        query = text.lower().split('research', 1)[-1].strip()
        
        if not query:
            say(
                text="🤔 What would you like me to research?\n"
                     "Example: `research AI trends in education`"
            )
            return
        
        # Acknowledge
        say(text=f"🔍 Researching: *{query}*\nThis might take a minute...")
        
        try:
            # Run research
            result = research_agent.run(query)
            
            findings = result.get('research_findings', 'No findings generated')
            output_path = result.get('output_path', 'N/A')
            
            if len(findings) > 3000:
                findings = findings[:3000] + "\n\n... (truncated)"
            
            say(
                text=f"✅ Research complete!\n\n"
                     f"{'='*40}\n"
                     f"{findings}\n"
                     f"{'='*40}\n\n"
                     f"📄 Full report: `{output_path}`"
            )
            
        except Exception as e:
            logger.error(f"Error: {e}")
            say(text=f"❌ Error during research:\n```{str(e)}```")


@app.event("message")
def handle_message_events(body, logger):
    """Catch-all for other messages (prevents unhandled event errors)"""
    logger.debug(body)


def main():
    """Start the Slack bot."""
    print("╔═══════════════════════════════════════════════════╗")
    print("║     Research Agent - Slack Bot Mode              ║")
    print("╚═══════════════════════════════════════════════════╝")
    print()
    print("🤖 Bot is starting...")
    print("📱 Listening for Slack messages...")
    print()
    print("Usage:")
    print("  • Mention bot: @ResearchBot [your query]")
    print("  • Direct message: research [your query]")
    print()
    print("Press Ctrl+C to stop")
    print()
    
    # Start the bot in Socket Mode (easier for development)
    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    handler.start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting bot: {e}")
        print("\nMake sure you have:")
        print("  1. SLACK_BOT_TOKEN in .env")
        print("  2. SLACK_APP_TOKEN in .env (for Socket Mode)")
        print("  3. Bot is installed to your workspace")