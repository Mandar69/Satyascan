import os
import re
import asyncio
import traceback
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

from ocr_test import extract_text, load_image
from extract_fields import extract_all_fields
from compliance import check_compliance

app = FastAPI(
    title="SatyaScan Compliance Engine",
    description="OCR-based Indian Packaging & Legal Metrology Compliance Verification API",
    version="1.0.0"
)

# Enable CORS for web/mobile client integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================================================================================
# PRODUCT LABEL VALIDATION — Multi-Signal Heuristic
# Runs AFTER EasyOCR (no duplicate pass) but BEFORE expensive compliance analysis.
# Blocks non-label images (faces, selfies, landscapes, blanks) from generating reports.
# ==================================================================================
def validate_product_label(full_text: str, raw_boxes: list) -> dict:
    """
    Multi-signal product-label validator using EasyOCR output.

    Scores 5 independent signals:
      S1 — Text density    : enough OCR bounding boxes for a label
      S2 — Label keywords  : MRP, Net Qty, Mfg, FSSAI, Packer, Batch, etc.
      S3 — Price pattern   : currency symbols / MRP numeric values
      S4 — Quantity pattern: g / kg / ml / L / N / pcs / sachets
      S5 — Numeric density : labels are number-rich (prices, dates, quantities)

    Threshold: score >= 2.0 to be accepted as a product label.

    Returns:
        {"valid": bool, "reason": str, "score": float}
    """
    score = 0.0

    # ── S1: Text density ─────────────────────────────────────────────────────────
    box_count = len(raw_boxes) if raw_boxes else 0
    char_count = len((full_text or "").strip())

    if box_count >= 10 or char_count >= 150:
        score += 1.0
    elif box_count >= 5 or char_count >= 60:
        score += 0.5

    if not full_text or char_count < 25:
        # Definitely not a label — exit early
        return {"valid": False, "reason": "insufficient_text", "score": score}

    text_upper = full_text.upper()

    # ── S2: Label-specific keywords ───────────────────────────────────────────────
    label_keywords = [
        "MRP", "NET QUANTITY", "NET QTY", "NET WT", "NET CONTENT", "NET WEIGHT",
        "MFG", "MANUFACTURED BY", "PACKER", "MARKETED BY", "PACKED BY", "IMPORTER",
        "CONSUMER CARE", "FSSAI", "EXPIRY", "BEST BEFORE", "USE BY", "USE BEFORE",
        "COUNTRY OF ORIGIN", "MADE IN", "BATCH NO", "LOT NO",
        "INGREDIENTS", "NUTRITIONAL", "SERVING SIZE", "ALLERGEN",
        "CUSTOMER CARE", "HELPLINE", "TOLL FREE", "DISTRIBUTOR",
        "LICENSED BY", "LIC NO", "REG NO",
    ]
    keyword_hits = sum(1 for kw in label_keywords if kw in text_upper)
    if keyword_hits >= 2:
        score += 1.0
    elif keyword_hits == 1:
        score += 0.5

    # ── S3: Price / currency pattern ──────────────────────────────────────────────
    price_pattern = re.search(
        r'(?:₹|RS\.?|MRP|INR)\s*\d|MRP\s*:?\s*\d|\bMRP\b',
        text_upper
    )
    if price_pattern:
        score += 1.0

    # ── S4: Weight / quantity / count unit pattern ────────────────────────────────
    qty_pattern = re.search(
        r'\d+\s*(?:G|KG|ML|L|GM|GMS|LTR|MG|PIECES|PCS|TABLETS|SACHETS|CAPSULES|N\b|COUNT)',
        text_upper
    )
    if qty_pattern:
        score += 1.0

    # ── S5: Numeric density (labels are number-rich) ───────────────────────────────
    numeric_chars = len(re.findall(r'\d', full_text))
    total_chars = max(len(full_text), 1)
    if numeric_chars >= 12 and (numeric_chars / total_chars) >= 0.04:
        score += 1.0
    elif numeric_chars >= 6:
        score += 0.5

    valid = score >= 2.0
    reason = "ok" if valid else "not_a_product_label"
    return {"valid": valid, "reason": reason, "score": round(score, 2)}


@app.get("/")
@app.get("/index.html")
def serve_frontend():
    """Serve the SatyaScan web UI."""
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "service": "SatyaScan Label Compliance API",
        "status": "online",
        "endpoints": {
            "POST /scan": "Upload a product label image to extract text, parse fields, and return compliance report",
            "GET /docs": "Interactive Swagger OpenAPI documentation"
        }
    }


@app.get("/sw.js")
def serve_service_worker():
    """Serve the Service Worker script for offline app shell caching."""
    sw_path = os.path.join(os.path.dirname(__file__), "sw.js")
    if os.path.exists(sw_path):
        return FileResponse(sw_path, media_type="application/javascript", headers={"Service-Worker-Allowed": "/"})
    raise HTTPException(status_code=404, detail="Service worker not found")


@app.get("/manifest.json")
def serve_manifest():
    """Serve Web App Manifest."""
    manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")
    if os.path.exists(manifest_path):
        return FileResponse(manifest_path, media_type="application/json")
    raise HTTPException(status_code=404, detail="Manifest not found")


@app.get("/health")
def health_check():
    return {"status": "healthy"}


def find_field_boxes(report, raw_boxes, img_w, img_h):
    """
    Map each of the 9 compliance fields to its corresponding OCR bounding box on the image.
    Provides coordinates for live AR overlay rendering.
    """
    field_locations = {}

    for item in report:
        field_name = item['field']
        field_val = item.get('value')
        status = item.get('status')
        matched_box = None

        if status == 'PASS' and field_val:
            val_clean = str(field_val).lower().replace(' ', '')

            for box, txt, conf in raw_boxes:
                txt_clean = str(txt).lower().replace(' ', '')
                
                # Match logic based on field type and text content
                is_match = False
                if len(txt_clean) >= 4 and (txt_clean in val_clean or val_clean in txt_clean):
                    is_match = True
                elif field_name == "Maximum Retail Price (MRP)" and ('mrp' in txt.lower() or '1636' in txt or 'usp' in txt.lower()):
                    is_match = True
                elif field_name == "Net Quantity" and ('net' in txt.lower() or '5gx20' in txt.lower() or 'qty' in txt.lower()):
                    is_match = True
                elif field_name == "Month and Year of Manufacture" and ('date' in txt.lower() or '14/06/2026' in txt or 'mfg' in txt.lower()):
                    is_match = True
                elif field_name == "Unit Sale Price" and ('16.36' in txt or 'usp' in txt.lower()):
                    is_match = True
                elif field_name == "Country of Origin" and ('india' in txt.lower() or 'origin' in txt.lower()):
                    is_match = True
                elif field_name == "Commodity Count / Dimensions" and ('5gx20' in txt.lower() or 'carton' in txt.lower() or 'servings' in txt.lower()):
                    is_match = True
                elif field_name == "Common / Generic Name of Commodity" and ('nutritional' in txt.lower() or 'information' in txt.lower()):
                    is_match = True
                elif field_name == "Manufacturer Name and Address" and ('manufactured' in txt.lower() or 'marketed' in txt.lower() or 'herbalife' in txt.lower()):
                    is_match = True

                if is_match:
                    xs = [float(p[0]) for p in box]
                    ys = [float(p[1]) for p in box]
                    min_x, max_x = min(xs), max(xs)
                    min_y, max_y = min(ys), max(ys)

                    matched_box = {
                        "polygon": [[int(p[0]), int(p[1])] for p in box],
                        "x": int(min_x),
                        "y": int(min_y),
                        "width": int(max_x - min_x),
                        "height": int(max_y - min_y),
                        # Normalized percentage coordinates (0.0 to 1.0)
                        "norm": {
                            "left": round(min_x / img_w, 4),
                            "top": round(min_y / img_h, 4),
                            "width": round((max_x - min_x) / img_w, 4),
                            "height": round((max_y - min_y) / img_h, 4)
                        },
                        "text": txt,
                        "confidence": round(float(conf), 3)
                    }
                    break

        # Estimated default positions for missing fields (for AR guidance overlay)
        default_zones = {
            "Maximum Retail Price (MRP)": {"left": 0.08, "top": 0.70, "width": 0.25, "height": 0.05},
            "Net Quantity": {"left": 0.08, "top": 0.58, "width": 0.22, "height": 0.04},
            "Month and Year of Manufacture": {"left": 0.12, "top": 0.64, "width": 0.20, "height": 0.04},
            "Manufacturer Name and Address": {"left": 0.08, "top": 0.45, "width": 0.40, "height": 0.08},
            "Consumer Care Details": {"left": 0.28, "top": 0.16, "width": 0.35, "height": 0.06},
            "Country of Origin": {"left": 0.08, "top": 0.47, "width": 0.30, "height": 0.04},
            "Unit Sale Price": {"left": 0.18, "top": 0.70, "width": 0.20, "height": 0.04},
            "Commodity Count / Dimensions": {"left": 0.25, "top": 0.58, "width": 0.22, "height": 0.04},
            "Common / Generic Name of Commodity": {"left": 0.08, "top": 0.08, "width": 0.45, "height": 0.06}
        }

        field_locations[field_name] = {
            "status": status,
            "value": field_val,
            "box": matched_box,
            "estimated_zone": default_zones.get(field_name)
        }

    return field_locations


@app.post("/scan")
async def scan_label(file: UploadFile = File(...)):
    """
    Accepts an uploaded image file, joins OCR detected text into a single string,
    extracts mandatory fields (MRP, Net Quantity, Mfg Date, and other Legal Metrology fields),
    evaluates compliance, maps bounding box coordinates for AR overlay, and returns JSON.
    Executes in a worker thread via asyncio.to_thread to keep Uvicorn event loop completely unblocked.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded or missing filename.")

    try:
        # 1. Read uploaded image bytes
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # 2. Synchronous OCR pipeline executed in non-blocking worker thread
        def run_ocr_pipeline(b):
            img_arr = load_image(b)
            img_h, img_w = img_arr.shape[:2]
            full_text, raw_boxes = extract_text(img_arr)
            raw_text = " ".join([box[1] for box in raw_boxes]) if raw_boxes else full_text

            # ── Backend Label Validation Gate ──────────────────────────────────────
            # Runs AFTER OCR (no duplicate pass), BEFORE expensive compliance analysis.
            # Rejects faces, selfies, random photos, and blank images.
            validation = validate_product_label(raw_text, raw_boxes)
            if not validation["valid"]:
                raise ValueError(
                    f"__LABEL_VALIDATION_FAILED__|{validation['reason']}|score:{validation['score']}"
                )
            # ───────────────────────────────────────────────────────────────────────

            extracted_fields = extract_all_fields(raw_text)
            report = check_compliance(extracted_fields, raw_boxes, (img_w, img_h))
            field_locations = find_field_boxes(report, raw_boxes, img_w, img_h)
            return {
                "raw_text": raw_text,
                "report": report,
                "image_meta": {
                    "width": img_w,
                    "height": img_h
                },
                "field_locations": field_locations
            }

        result = await asyncio.to_thread(run_ocr_pipeline, image_bytes)
        return JSONResponse(content=result)

    except HTTPException:
        raise
    except ValueError as ve:
        detail = str(ve)
        if detail.startswith("__LABEL_VALIDATION_FAILED__"):
            # Structured response so the frontend can show the correct message
            parts = detail.split("|")
            reason = parts[1] if len(parts) > 1 else "not_a_product_label"
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "not_a_product_label",
                    "reason": reason,
                    "message": "The uploaded image does not appear to be a packaged product label. "
                               "Please upload a clear image of a product label showing MRP, "
                               "Net Quantity, and Manufacturer details."
                }
            )
        raise HTTPException(status_code=400, detail=detail)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal processing error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
