import io
import os
import gc
import easyocr
import numpy as np
import torch
from PIL import Image, ImageOps

# Limit PyTorch to single-thread evaluation to eliminate multi-core memory duplication
torch.set_num_threads(1)
try:
    torch.set_num_interop_threads(1)
except Exception:
    pass

# Support HEIF/HEIC image formats (common on iOS devices)
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

# Initialize EasyOCR reader instance
reader = easyocr.Reader(['en'], gpu=False, verbose=False)


def load_image(image_input, max_dimension=960):
    """
    Load an image from a file path, raw bytes, or BytesIO.
    Supports broad format range (JPEG, PNG, HEIC/HEIF, TIFF, WebP, etc.) and auto-orientates EXIF tags.
    Downscales large photos to fit within max_dimension to keep memory lightweight (<100MB) and fast.
    """
    try:
        if isinstance(image_input, (bytes, bytearray)):
            pil_img = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, io.BytesIO):
            pil_img = Image.open(image_input)
        elif isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Image file not found: '{image_input}'")
            pil_img = Image.open(image_input)
        elif isinstance(image_input, Image.Image):
            pil_img = image_input
        elif isinstance(image_input, np.ndarray):
            return image_input
        else:
            raise TypeError(f"Unsupported image input type: {type(image_input)}")

        # Correct orientation based on EXIF tags (e.g. iPhone photos)
        pil_img = ImageOps.exif_transpose(pil_img)
        # Convert to standard RGB mode
        pil_img = pil_img.convert('RGB')

        # Optimize memory: downscale if image exceeds max_dimension
        if max(pil_img.size) > max_dimension:
            scale = max_dimension / max(pil_img.size)
            new_size = (int(pil_img.width * scale), int(pil_img.height * scale))
            pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)

        # Convert to numpy array for EasyOCR
        return np.array(pil_img)
    except Exception as e:
        raise ValueError(f"Failed to load image: {e}") from e


def extract_text(image_input):
    """
    Extract text from an image (file path, bytes, or numpy array).
    Returns (full_text: str, results: list).
    Uses torch.inference_mode() and 1 thread to guarantee strict memory bounds (<100MB).
    """
    if isinstance(image_input, np.ndarray):
        img = image_input
    else:
        img = load_image(image_input)

    with torch.inference_mode():
        results = reader.readtext(
            img,
            canvas_size=960,
            mag_ratio=1.0,
            batch_size=1,
            workers=0
        )

    gc.collect()
    full_text = " ".join([r[1] for r in results])
    return full_text, results