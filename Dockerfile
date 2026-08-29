# ============================================================
# SatyaScan — Legal Metrology Compliance Engine
# Multi-stage Docker build for Railway.app deployment
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

# Install modern PyTorch CPU wheel (supports NumPy 2.x natively)
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

# Pre-download and cache EasyOCR model weights + verify complete OCR pipeline
RUN python -c "\
import easyocr, numpy, torch; \
print(f'NumPy version: {numpy.__version__}'); \
print(f'PyTorch version: {torch.__version__}'); \
t = torch.tensor([1, 2, 3]); \
print(f'PyTorch tensor-to-numpy verification: {t.numpy()}'); \
print('Downloading & validating EasyOCR model weights...'); \
reader = easyocr.Reader(['en'], gpu=False, verbose=False); \
test_img = numpy.ones((100, 300, 3), dtype=numpy.uint8) * 255; \
res = reader.readtext(test_img); \
print('EASYOCR PIPELINE VERIFIED SUCCESSFULLY!')"

# --- Stage 2: Runtime ---
FROM python:3.12-slim

WORKDIR /app

# Runtime libraries only
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

# Copy pre-downloaded EasyOCR weights
COPY --from=builder /root/.EasyOCR /root/.EasyOCR

# Copy application source code
COPY main.py .
COPY ocr_test.py .
COPY extract_fields.py .
COPY compliance.py .
COPY index.html .
COPY sw.js .
COPY manifest.json .

ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
