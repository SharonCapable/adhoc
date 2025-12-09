FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed
# RUN apt-get update && apt-get install -y git

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all agent code
COPY . .

# Service account key should be mounted at runtime for security
# Mount it when running: -v /path/to/service-account.json:/app/service-account.json

# Expose port
EXPOSE 8000

# Run the API server
CMD echo "$GOOGLE_SERVICE_ACCOUNT_JSON" > service-account.json && uvicorn api_server:app --host 0.0.0.0 --port 8000