FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server files
COPY bookmarks-server.py .
COPY bookmarks_manager.py .
COPY bookmarks_importer.py .
COPY config.py .
COPY static/ ./static/

# Create directories for data, logs, and config
RUN mkdir -p /data/bookmarks /data/logs /app/config

# Set environment variables
ENV BOOKMARKS_DIR=/data/bookmarks
ENV DEBUG=INFO
ENV PORT=9080
ENV LOG_FILE=/data/logs/bookmarks-server.log

# Expose port
EXPOSE 9080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9080/ || exit 1

# Run the server
CMD ["python", "bookmarks-server.py"] 