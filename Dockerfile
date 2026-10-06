# ============================================================
# GameWatch Production Container (Step 2: $0/Month Architecture)
# Targeted for Render / Koyeb / Fly.io free tiers
# ============================================================
FROM python:3.11-slim

# Install system dependencies for headless OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application source code
COPY . .

# Set production environment variables
ENV PYTHONUNBUFFERED=1 \
    PORT=5000 \
    FLASK_ENV=production \
    OPENCV_FFMPEG_CAPTURE_OPTIONS="rtsp_transport;tcp|fflags;nobuffer|max_delay;0|flags;low_delay"

EXPOSE 5000

# Health check endpoint for automated cloud monitoring
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Launch production server
CMD ["python", "app_server.py"]
