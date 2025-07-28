FROM python:3.10-slim

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# ⏱️ Set longer timeout for pip
ENV PIP_DEFAULT_TIMEOUT=100

# 🗂️ Optional: Allow pip caching if needed
ENV PIP_NO_CACHE_DIR=off

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Pre-install wheels (optional)
COPY wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# Copy requirements and install remaining packages
COPY app/requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Copy application code
COPY app .

# Run app
ENTRYPOINT ["python", "main.py"]
