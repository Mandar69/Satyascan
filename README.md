# SatyaScan — Legal Metrology Packaging Compliance Engine

**AI-powered packaging label compliance scanner** under India's Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6.

---

## Features

- ✅ **9-field Legal Metrology audit** (Manufacturer, MRP, Net Qty, Mfg Date, Consumer Care, Country of Origin, USP, Commodity Count, Generic Name)
- 🔍 **Live AR bounding box overlay** on scanned label image (EasyOCR coordinates)
- 📄 **Auto-generated official PDF violation notice** (jsPDF, downloadable)
- 🌐 **Bilingual UI** — English + Hindi (i18n)
- 📷 **Upload or camera capture** support (including iPhone HEIC)
- 💬 **Bilingual FAQ chatbot** (rule-based, offline)
- 📲 **PWA / Service Worker** for offline app-shell caching
- 👤 **Onboarding flow** with localStorage auth (Inspector / Consumer roles)

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI + Uvicorn |
| **OCR Engine** | EasyOCR (PyTorch, CPU) |
| **Image Processing** | Pillow, pillow-heif, OpenCV |
| **Frontend** | Vanilla HTML/CSS/JS (single `index.html`) |
| **PDF Generation** | jsPDF + AutoTable (client-side) |
| **Icons** | Lucide Icons (CDN) |
| **Fonts** | Space Grotesk + Inter + Noto Sans Devanagari (Google Fonts) |
| **Deployment** | Docker on Railway.app |

---

## Local Development

```bash
# Clone the repository
git clone <your-repo-url>
cd satyascan

# Create a virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Open in browser
open http://localhost:8000
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Serves the SatyaScan web UI |
| `POST` | `/scan` | Accepts image upload; returns compliance report JSON |
| `GET` | `/health` | Health check for Railway deployment |
| `GET` | `/docs` | Interactive Swagger API documentation |

### POST `/scan` Response Format

```json
{
  "raw_text": "...",
  "report": [
    {
      "field": "Maximum Retail Price (MRP)",
      "value": "1636.00",
      "status": "PASS",
      "fix_instruction": ""
    }
  ],
  "image_meta": { "width": 3024, "height": 4032 },
  "field_locations": {
    "Maximum Retail Price (MRP)": {
      "status": "PASS",
      "value": "1636.00",
      "box": {
        "norm": { "left": 0.09, "top": 0.71, "width": 0.10, "height": 0.03 }
      }
    }
  }
}
```

---

## Deployment on Railway.app

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Create project and deploy
railway init
railway up
```

Railway will automatically build the Dockerfile and deploy the service.  
The live URL will be visible on your Railway dashboard.

---

## Legal Reference

**Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6**  
Ministry of Consumer Affairs, Food & Public Distribution, Government of India.
