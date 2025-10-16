# Chat Yapper Dockerfile
# Multi-stage build for smaller final image

# Stage 1: Build frontend
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install frontend dependencies
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build frontend (outputs to ../backend/public via vite.config.js)
RUN npm run build

# Stage 2: Python application
FROM python:3.10-slim

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend requirements
COPY requirements.txt ./
COPY backend/requirements.txt ./backend/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/ ./backend/
COPY main.py ./
COPY icon.ico ./

# Copy built frontend from builder stage
COPY --from=frontend-builder /app/backend/public ./backend/public/

# Create directories for persistent data
RUN mkdir -p /data/voice_avatars /data/audio

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000

# Expose the application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/status').read()"

# Run the application
CMD ["python", "main.py"]
