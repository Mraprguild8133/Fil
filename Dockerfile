FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 5000

# Health check (ensure the app is responding)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:5000/ || exit 1

# Run the app
CMD ["python", "main.py"]
