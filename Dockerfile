# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/agent_backend

# Set work directory
WORKDIR /app

# Install system dependencies (needed for lxml and others)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY agent_backend/requirements.txt /app/agent_backend/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/agent_backend/requirements.txt

# Copy the rest of the application
COPY agent_backend /app/agent_backend
COPY drafts /app/drafts
COPY website/src/content /app/website/src/content
# Note: We copy drafts and content folders because the scripts write to them. 
# In production with Docker Compose, these should be volumes.

# Expose port
EXPOSE 8000

# Run the API server
CMD ["uvicorn", "agent_backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
