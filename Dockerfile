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

# Step 1: Pin NumPy <2 first to avoid ABI incompatibility with PyTorch CPU wheels
# PyTorch CPU-only wheels from the /whl/cpu index are compiled against NumPy 1.x.
# Using NumPy 2.x causes: "_ARRAY_API not found" → "Numpy is not available" crash.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "numpy>=1.26,<2"

# Step 2: Install PyTorch CPU-only (avoids downloading 2GB CUDA build)
RUN pip install --no-cache-dir \
        torch==2.2.2 \
        torchvision==0.17.2 \
        --index-url https://download.pytorch.org/whl/cpu

# Step 3: Install EasyOCR (will use the already-installed torch + numpy)
RUN pip install --no-cache-dir easyocr==1.7.2

# Step 4: Install remaining app dependencies
RUN pip install --no-cache-dir \
        fastapi \
        uvicorn \
        python-multipart \
        pillow \
        pillow-heif \
        opencv-python-headless \
        scikit-image \
        scipy \
        shapely \
        pyclipper \
        python-bidi

# Pre-download EasyOCR English model weights during build
# (so the container doesn't download them on first user request)
RUN python -c "\
import easyocr; \
print('Downloading EasyOCR English model weights...'); \
reader = easyocr.Reader(['en'], gpu=False, verbose=False); \
print('Model weights cached successfully.')"

# Verify numpy + torch actually work together
RUN python -c "\
import numpy; print(f'NumPy: {numpy.__version__}'); \
import torch; print(f'PyTorch: {torch.__version__}'); \
t = torch.tensor([1.0, 2.0, 3.0]); n = t.numpy(); \
print(f'torch→numpy OK: {n}'); \
print('All imports verified successfully.')"

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
