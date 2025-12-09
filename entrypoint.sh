#!/bin/sh

# If the GOOGLE_SERVICE_ACCOUNT_JSON env var exists, write it to service-account.json
if [ -n "$GOOGLE_SERVICE_ACCOUNT_JSON" ]; then
    echo "Creating service-account.json from environment variable..."
    echo "$GOOGLE_SERVICE_ACCOUNT_JSON" > /app/service-account.json
else
    echo "WARNING: GOOGLE_SERVICE_ACCOUNT_JSON not set. service-account.json may be missing."
fi

# Run the CMD from the Dockerfile
exec "$@"