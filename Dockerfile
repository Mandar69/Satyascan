# ============================================================
# SatyaScan — Legal Metrology Compliance Engine
# Multi-stage Docker build for Hugging Face Spaces & Cloud
# ============================================================

# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

WORKDIR /build

# System dependencies for OpenCV, Pillow, HEIC, etc.
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

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install PyTorch CPU-only wheel
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install EasyOCR and all application dependencies
RUN pip install --no-cache-dir \
    easyocr \
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

# Pre-download and cache EasyOCR model weights during build
RUN python -c "\
import easyocr, numpy, torch; \
print(f'NumPy version: {numpy.__version__}'); \
print(f'PyTorch version: {torch.__version__}'); \
reader = easyocr.Reader(['en'], gpu=False, verbose=False); \
test_img = numpy.ones((100, 300, 3), dtype=numpy.uint8) * 255; \
res = reader.readtext(test_img); \
print('EASYOCR MODEL PRE-DOWNLOADED & VERIFIED!')"

# --- Stage 2: Runtime ---
FROM python:3.12-slim

# Create user with UID 1000 for Hugging Face Spaces security
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

USER root
# Install runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libheif-dev \
    libde265-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy packages from builder
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy pre-downloaded EasyOCR weights to user home & root
COPY --from=builder /root/.EasyOCR /home/user/.EasyOCR
COPY --from=builder /root/.EasyOCR /root/.EasyOCR
RUN chown -R user:user /home/user/.EasyOCR

# Copy application source code
COPY --chown=user:user main.py .
COPY --chown=user:user ocr_test.py .
COPY --chown=user:user extract_fields.py .
COPY --chown=user:user compliance.py .
COPY --chown=user:user index.html .
COPY --chown=user:user sw.js .
COPY --chown=user:user manifest.json .

USER user

# Hugging Face default port is 7860
ENV PORT=7860
EXPOSE 7860

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7860} --workers 1"]
