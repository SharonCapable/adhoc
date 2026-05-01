#!/bin/sh

# 1. Handle Google Service Account JSON (using Python for safe writing)
if [ -n "$GOOGLE_SERVICE_ACCOUNT_JSON" ]; then
    echo "Writing service-account.json..."
    python3 -c "import os, json; data = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'); f = open('/app/service-account.json', 'w'); f.write(data); f.close()"
else
    echo "WARNING: GOOGLE_SERVICE_ACCOUNT_JSON not set."
fi

# 2. Start the Slack Bot in the background
echo "Starting Slack Bot..."
python3 run_slack.py &

# 3. Start the API Server (foreground)
echo "Starting API Server..."
exec "$@"