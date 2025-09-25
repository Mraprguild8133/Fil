FROM python:3.11-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir .

# Copy app code
COPY . .

EXPOSE 5000

# Health check
HEALTHCHECK CMD curl -f http://localhost:5000/ || exit 1

CMD ["python", "main.py"]
