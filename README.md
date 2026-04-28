# MediSeen Backend

FastAPI-based medical image diagnostic backend for the MediSeen Android app.

## Features

- **Image Upload:** Accept chest X-ray images via multipart form-data
- **AI Diagnostics:** Google Gemini-powered disease classification with explainability
- **Heatmap Generation:** Visual explanations using Grad-CAM
- **Cloud Storage:** Cloudinary (primary) or Firebase Storage (fallback)
- **Rate Limiting:** Per-user diagnosis limits to control API costs
- **CORS Support:** Universal Android device support (Capacitor origins)

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export GEMINI_API_KEY="your-key"
export CLOUDINARY_NAME="your-name"
export CLOUDINARY_KEY="your-key"
export CLOUDINARY_SECRET="your-secret"

# Run backend
python -m uvicorn main:app --reload
```

Backend runs at: `http://127.0.0.1:8000`

API docs available at:
- OpenAPI: `http://127.0.0.1:8000/openapi.json`
- Swagger UI: `http://127.0.0.1:8000/docs`

## Deployment to Render

See [ANDROID_DEPLOYMENT_GUIDE.md](ANDROID_DEPLOYMENT_GUIDE.md) for step-by-step instructions.

### Quick Deploy

1. Connect your GitHub repo to Render
2. Render auto-detects `render.yaml` blueprint
3. Set environment variables in Render dashboard:
   - `GEMINI_API_KEY`
   - `CLOUDINARY_NAME`, `CLOUDINARY_KEY`, `CLOUDINARY_SECRET`
4. Deploy

After deployment, copy the service URL and update the Android app's `NEXT_PUBLIC_API_URL`.

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GEMINI_API_KEY` | Yes | Google Gemini API for diagnosis |
| `CLOUDINARY_NAME` | Yes | Cloudinary project name |
| `CLOUDINARY_KEY` | Yes | Cloudinary API key |
| `CLOUDINARY_SECRET` | Yes | Cloudinary API secret |
| `APP_ENV` | No | `production` or `development` |
| `PORT` | No | Server port (default: 10000) |
| `ALLOWED_ORIGINS` | No | CORS allowed origins |
| `FIREBASE_STORAGE_BUCKET` | No | Firebase fallback storage |

## API Endpoints

### POST /diagnose

Upload image + symptoms for diagnosis.

**Request:**
```bash
curl -X POST http://localhost:8000/diagnose \
  -F "image=@chest-xray.png" \
  -F "symptoms=chest pain, cough"
```

**Response:**
```json
{
  "diagnosis": "Pneumonia",
  "confidence": 0.95,
  "heatmap_url": "https://cloudinary.com/...",
  "explanation": "Detected consolidation in left lung...",
  "clinical_features": ["lung_opacity", "consolidation"]
}
```

### GET /docs

Interactive API documentation (Swagger UI).

### GET /openapi.json

OpenAPI 3.1.0 specification.

## Architecture

```
backend/
├── main.py              # FastAPI app, endpoints, CORS
├── services/
│   ├── storage_svc.py   # Cloudinary/Firebase abstraction
│   ├── firebase_svc.py  # Firebase initialization
│   └── gemini_svc.py    # Google Gemini API calls
├── Dockerfile           # Docker containerization
└── requirements.txt     # Python dependencies
```

## Technologies

- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **Google Gemini** - AI diagnostics
- **Cloudinary** - Image storage
- **Firebase Admin SDK** - Firestore cache
- **Python-Multipart** - Form data parsing
- **python-dotenv** - Environment configuration

## License

Built for Hackverse 2.0 hackathon.

## Support

For issues:
1. Check [ANDROID_DEPLOYMENT_GUIDE.md](ANDROID_DEPLOYMENT_GUIDE.md) troubleshooting section
2. Review Render logs: `render.com` dashboard
3. Test locally: `python -m uvicorn main:app --reload`
