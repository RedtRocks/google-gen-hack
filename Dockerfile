# Use Python slim image
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py ./
COPY storage_service.py ./

# Copy pre-built frontend
COPY client/dist/ ./client/dist/

# Expose port
EXPOSE 8080

# Environment variables
ENV PORT=8080
ENV PYTHONPATH=/app

# Start the application
CMD ["python", "main.py"]