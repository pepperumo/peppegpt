# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set Tesseract environment variable
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/

# Install system dependencies including Tesseract OCR, libraries for EasyOCR/OpenCV, and Playwright deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libleptonica-dev \
    pkg-config \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    # Playwright dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r ragpipeline && useradd -r -g ragpipeline ragpipeline

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set Playwright browsers path to a location accessible by non-root user
ENV PLAYWRIGHT_BROWSERS_PATH=/app/.playwright

# Install Playwright browsers for Crawl4AI web crawling
# Must be done after pip install (which installs playwright via crawl4ai)
RUN playwright install chromium && \
    playwright install-deps chromium

# Copy application code
COPY . .

# Make entrypoint executable
RUN chmod +x docker_entrypoint.py

# Create data directories and set permissions
RUN mkdir -p /app/Local_Files/data /app/Google_Drive/credentials /app/.cache && \
    chown -R ragpipeline:ragpipeline /app

# Pre-download EasyOCR models during build (as root before switching user)
# This avoids runtime downloads and improves first-run performance
ENV HOME=/app
RUN python -c "import easyocr; reader = easyocr.Reader(['en'], gpu=False, download_enabled=True, verbose=False); print('✓ EasyOCR models pre-downloaded')" && \
    chown -R ragpipeline:ragpipeline /app/.EasyOCR

# Switch to non-root user
USER ragpipeline

# Environment variables with defaults
ENV RAG_PIPELINE_TYPE=local
ENV RUN_MODE=continuous
ENV CHECK_INTERVAL=60
ENV PYTHONUNBUFFERED=1

# Entrypoint - let docker_entrypoint.py handle defaults from environment variables
ENTRYPOINT ["python", "docker_entrypoint.py"]