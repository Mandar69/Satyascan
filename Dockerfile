# ============================================================
# SatyaScan — Legal Metrology Compliance Engine
# Multi-stage Docker build for Railway.app deployment
#
# Stage 1: Builder — install all Python deps incl. PyTorch/EasyOCR
# Stage 2: Runtime — lean final image serving the FastAPI app
# ============================================================

# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

WORKDIR /build

# System libs needed by OpenCV, Pillow, scikit-image, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libheif-dev \
    libde265-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY requirements.txt .

# Install PyTorch CPU-only first (avoids downloading 2GB CUDA build)
# This significantly reduces final image size on Railway (no CUDA drivers needed)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        torch==2.2.2 \
        torchvision==0.17.2 \
        --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir easyocr==1.7.2 && \
    pip install --no-cache-dir \
        fastapi==0.141.1 \
        uvicorn==0.52.4 \
        python-multipart==0.0.32 \
        pillow==12.3.0 \
        pillow-heif==1.5.0 \
        numpy==2.5.2 \
        opencv-python-headless==5.0.0.93 \
        scikit-image==0.26.0 \
        scipy==1.18.1 \
        shapely==2.1.2 \
        pyclipper==1.4.0 \
        python-bidi==0.6.11

# Pre-download EasyOCR English model weights during build
# (so the container doesn't download them on first user request)
RUN python -c "\
import easyocr; \
print('Downloading EasyOCR English model weights...'); \
reader = easyocr.Reader(['en'], gpu=False, verbose=False); \
print('Model weights cached successfully.')"

# --- Stage 2: Runtime ---
FROM python:3.12-slim

WORKDIR /app

# Only copy runtime system libs (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libheif-dev \
    libde265-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy EasyOCR cached model weights from builder
COPY --from=builder /root/.EasyOCR /root/.EasyOCR

# Copy application source files
COPY main.py .
COPY ocr_test.py .
COPY extract_fields.py .
COPY compliance.py .
COPY index.html .
COPY sw.js .
COPY manifest.json .

# Railway injects PORT env var — uvicorn must bind to it
ENV PORT=8000
EXPOSE 8000

# Run FastAPI via uvicorn. Railway sets $PORT dynamically.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
