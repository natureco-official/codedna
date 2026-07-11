FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for tree-sitter
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install CodeDNA
COPY . .
RUN pip install --no-cache-dir .

# Default command
CMD ["codedna", "serve", "--host", "0.0.0.0", "--port", "8000"]
