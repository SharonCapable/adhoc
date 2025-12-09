FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy entrypoint script and make it executable
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Expose port
EXPOSE 8000

# Set entrypoint to our script
ENTRYPOINT ["./entrypoint.sh"]

# Start the server (CMD is passed to entrypoint)
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]