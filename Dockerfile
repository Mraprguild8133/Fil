FROM python:3.11-slim

WORKDIR /app


# Copy and install dependencies
COPY requirements.txt 
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 5000

# Run the app
CMD ["python", "main.py"]
