import os
import uuid
import traceback
from io import BytesIO

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles  # <--- Added for URL access
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image, UnidentifiedImageError


# Firebase
try:
    from backend.services.firebase_svc import (
        init_firebase,
        check_and_increment_rate_limit,
        get_image_hash,
        get_cached_diagnosis,
        save_diagnosis_cache,
        increment_cache_hit,
        save_diagnosis_record,
        get_db,
    )
    from backend.services.storage_svc import upload_image
except ModuleNotFoundError:
    from services.firebase_svc import (
        init_firebase,
        check_and_increment_rate_limit,
        get_image_hash,
        get_cached_diagnosis,
        save_diagnosis_cache,
        increment_cache_hit,
        save_diagnosis_record,
        get_db,
    )
    from services.storage_svc import upload_image
from firebase_admin import auth, firestore

# Graph Pipeline
import sys
sys.path.append("..")

from model.graph import build_graph

load_dotenv()

app = FastAPI(title="Mediseen Backend")

# ---------------------------------------------------
# 0️⃣ Path Configuration & Static Mounting
# ---------------------------------------------------
# This ensures we are always in the 'backend' folder context
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serves files at: http://localhost:8000/uploads/
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
# ---------------------------------------------------
# Build LangGraph once
# ---------------------------------------------------
graph = build_graph()

# Restrict CORS to explicit origins from env instead of wildcard.
_allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "").strip()
_app_env = os.getenv("APP_ENV", os.getenv("ENV", "development")).lower()

# Always include Capacitor origins for native app support on ALL devices
_default_origins = "http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:3001,http://localhost:3001,http://localhost,capacitor://localhost,capacitor://app,file://,http://192.168.1.7:8000,http://192.168.1.7:3000"

if not _allowed_origins_raw:
    if _app_env == "production":
        # In production, include Capacitor origins to support all Android devices
        _allowed_origins_raw = "capacitor://localhost,capacitor://app,file://,https://your-frontend.onrender.com"
    else:
        _allowed_origins_raw = _default_origins

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in _allowed_origins_raw.split(",")
    if origin.strip()
]

# Function to allow any Capacitor origin (works on all phones)
def is_allowed_origin(origin: str) -> bool:
    """Check if origin is allowed, with special handling for Capacitor"""
    # Allow all Capacitor origins (capacitor://anything)
    if origin.startswith("capacitor://"):
        return True
    # Allow file:// protocol for local files
    if origin.startswith("file://"):
        return True
    # Allow localhost and loopback origins used by Capacitor web/runtime bridges
    if origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
        return True
    # Allow explicit whitelisted origins
    return origin in ALLOWED_ORIGINS

ALLOWED_UPLOAD_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
ALLOWED_IMAGE_EXTENSIONS = {
    "jpeg": ".jpg",
    "png": ".png",
    "webp": ".webp",
}
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MAX_SYMPTOMS_LENGTH = int(os.getenv("MAX_SYMPTOMS_LENGTH", "2000"))
MAX_IMAGE_PIXELS = int(os.getenv("MAX_IMAGE_PIXELS", "50000000"))

# 1️⃣ CORS - Allow all Capacitor origins for universal Android device support
class CORSOriginMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            origin = dict(scope.get("headers", [])).get(b"origin", b"").decode()
            if is_allowed_origin(origin):
                async def send_with_cors(message):
                    if message["type"] == "http.response.start":
                        headers = list(message.get("headers", []))
                        headers.append((b"access-control-allow-origin", origin.encode()))
                        headers.append((b"access-control-allow-credentials", b"true"))
                        headers.append((b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS"))
                        headers.append((b"access-control-allow-headers", b"*"))
                        headers.append((b"access-control-expose-headers", b"*"))
                        headers.append((b"access-control-max-age", b"600"))
                        message["headers"] = headers
                    await send(message)
                
                if scope.get("method") == "OPTIONS":
                    await send_with_cors({
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [],
                    })
                    await send({
                        "type": "http.response.body",
                        "body": b"",
                    })
                    return
                
                await self.app(scope, receive, send_with_cors)
                return
        
        await self.app(scope, receive, send)

app.add_middleware(CORSOriginMiddleware)

# 2️⃣ Firebase Init
init_firebase() # Centralized check-and-init

# 3️⃣ Request Models
def verify_bearer_token(authorization: str = Header(default="")):
    # Development bypass: when not in production, allow a special token 'dev'
    # to simplify local testing without Firebase. DO NOT enable in production.
    app_env = os.getenv("APP_ENV", os.getenv("ENV", "development")).lower()
    if app_env != "production" and authorization.strip() == "Bearer dev":
        return {"uid": "dev-user", "email": "dev@local", "dev": True}

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization[len("Bearer "):].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing Firebase token")

    try:
        return auth.verify_id_token(token, check_revoked=True)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Firebase token")

# 4️⃣ Health Check
@app.get("/")
def root():
    return {"status": "Mediseen API running"}

# 5️⃣ Verify Firebase Token
@app.post("/auth/verify")
async def verify_token(_decoded_token: dict = Depends(verify_bearer_token)):
    uid = _decoded_token.get("uid")
    db = get_db()
    has_profile = False
    profile_data = {}
    
    if db:
        user_doc = db.collection("users").document(uid).get()
        if user_doc.exists:
            has_profile = True
            profile_data = user_doc.to_dict()
            profile_data.pop("created_at", None) # Timestamp not serializable easily
            profile_data.pop("updated_at", None)

    return {
        "status": "verified", 
        "has_profile": has_profile,
        "uid": uid,
        "profile": profile_data
    }


@app.post("/auth/register")
async def register_user(
    request: dict,
    _decoded_token: dict = Depends(verify_bearer_token),
):
    """Save user profile data to Firestore after Firebase signup."""
    uid = _decoded_token.get("uid")
    if not uid:
        raise HTTPException(status_code=400, detail="Missing user id in token")

    email = _decoded_token.get("email")
    name = request.get("name", "").strip()
    role = request.get("role", "patient").lower()

    if not name:
        raise HTTPException(status_code=400, detail="User name is required")
    
    if role not in ["doctor", "patient"]:
        raise HTTPException(status_code=400, detail="Role must be 'doctor' or 'patient'")

    try:
        db = get_db()
        if not db:
            raise HTTPException(status_code=500, detail="Database connection failed")

        # Save user profile to Firestore
        db.collection("users").document(uid).set(
            {
                "uid": uid,
                "name": name,
                "email": email,
                "role": role,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
            merge=True
        )

        # Set custom claims for role-based access
        auth.set_custom_user_claims(uid, {"role": role})

        return {"status": "registered", "uid": uid, "name": name, "role": role}
    except Exception as e:
        print(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save user profile")


@app.post("/auth/disable-account")
async def disable_account(_decoded_token: dict = Depends(verify_bearer_token)):
    uid = _decoded_token.get("uid")
    if not uid:
        raise HTTPException(status_code=400, detail="Missing user id in token")

    try:
        auth.update_user(uid, disabled=True)
        auth.revoke_refresh_tokens(uid)
        return {"status": "disabled"}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to disable account")

# ---------------------------------------------------
# 6️⃣ AI Diagnosis Endpoint
# ---------------------------------------------------
@app.post("/diagnose")
async def diagnose(
    image: UploadFile = File(...),
    symptoms: str = Form(...),
    client_platform: str = Header(default="web", alias="X-Client-Platform"),
    _decoded_token: dict = Depends(verify_bearer_token),
):
    try:
        uid = _decoded_token.get("uid", "unknown")
        session_id = str(uuid.uuid4())

        # ── 1. Validate file ──────────────────────────────────────────────
        # In production, enforce that the declared multipart content-type is an allowed image MIME.
        # In non-production (dev/test) accept uploads even if the client sends a generic content-type
        # because some tools (PowerShell curl, etc.) may not set the part MIME correctly.
        if _app_env == "production":
            if image.content_type not in ALLOWED_UPLOAD_MIME_TYPES:
                raise HTTPException(status_code=400, detail="Unsupported image format")
        else:
            if image.content_type not in ALLOWED_UPLOAD_MIME_TYPES:
                print(f"WARNING: non-standard upload content_type={image.content_type}; continuing in dev mode")

        symptoms = (symptoms or "").strip()
        if len(symptoms) > MAX_SYMPTOMS_LENGTH:
            raise HTTPException(
                status_code=400,
                detail=f"Symptoms text too long. Max length is {MAX_SYMPTOMS_LENGTH} characters",
            )

        image_bytes = await image.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        if len(image_bytes) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB"
            )

        # Validate file signature and bound image dimensions to limit decompression bombs.
        try:
            with Image.open(BytesIO(image_bytes)) as pil_img:
                detected_format = (pil_img.format or "").lower()
                width, height = pil_img.size
        except UnidentifiedImageError:
            raise HTTPException(status_code=400, detail="File content does not match a supported image format")

        if detected_format not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Unsupported image content format")

        if width * height > MAX_IMAGE_PIXELS:
            raise HTTPException(
                status_code=400,
                detail=f"Image dimensions too large. Max pixel count is {MAX_IMAGE_PIXELS}",
            )

        # ── 2. Rate limit check (2 per user per day) ──────────────────────
        # In dev mode, skip rate limiting entirely to allow unlimited testing
        if _app_env == "production":
            rate = check_and_increment_rate_limit(uid)
            if not rate["allowed"]:
                raise HTTPException(
                    status_code=429,
                    detail=f"Daily limit reached. You can run {rate['limit']} diagnoses per day. Try again tomorrow."
                )

        # ── 3. Cache check (same image = instant result) ──────────────────
        image_hash = get_image_hash(image_bytes)
        cache_key = f"{uid}_{image_hash}"
        cached = get_cached_diagnosis(cache_key)
        if cached:
            increment_cache_hit(cache_key)
            # Still save the record for data collection
            save_diagnosis_record(uid, session_id, symptoms, cached, cached.get("image_url", ""), platform=client_platform)
            return {**cached, "session_id": session_id, "cached": True}

        # ── 4. Save image locally ─────────────────────────────────────────
        extension = ALLOWED_IMAGE_EXTENSIONS[detected_format]

        image_filename = f"{session_id}_input{extension}"
        image_path = os.path.join(UPLOAD_DIR, image_filename)

        with open(image_path, "wb") as buffer:
            buffer.write(image_bytes)

        # ── 5. Upload original to Firebase Storage ────────────────────────
        image_url = upload_image(image_path, f"uploads/{session_id}/original{extension}")

        # ── 6. Run AI pipeline ────────────────────────────────────────────
        state = {
            "session_id": session_id,
            "image_path": image_path,
            "image_url": image_url,
            "user_symptoms": symptoms,
            "prediction": "",
            "confidence_score": 0.0,
            "explanation": "",
            "db_context": "",
            "final_report": "",
            "heatmap_path": "",
            "report_path": "",
            "report_url": ""
        }

        result = graph.invoke(state)

        heatmap_file = os.path.basename(result["heatmap_path"])
        report_file = os.path.basename(result["report_path"])

        # ── 7. Cleanup original upload ────────────────────────────────────
        try:
            os.remove(image_path)
        except OSError as cleanup_error:
            print(f"WARNING: Could not remove temporary file {image_path}: {cleanup_error}")

        # ── 8. Build response ─────────────────────────────────────────────
        response = {
            "session_id": session_id,
            "diagnosis": result["prediction"],
            "confidence": result["confidence_score"],
            "explanation": result["final_report"],
            "heatmap_url": result.get("heatmap_url", f"/uploads/{heatmap_file}"),
            "report_url": result.get("report_url", f"/uploads/{report_file}"),
            "image_url": image_url,
            "cached": False
        }

        # ── 9. Save to cache + data collection ───────────────────────────
        save_diagnosis_cache(cache_key, response)
        save_diagnosis_record(uid, session_id, symptoms, response, image_url, platform=client_platform)

        return response

    except HTTPException:
        raise
    except Exception as e:
        print("ERROR: DIAGNOSIS ERROR")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Diagnosis pipeline failed")

# 7️⃣ Usage endpoint — how many diagnoses left today
@app.get("/diagnose/usage")
def get_usage(_decoded_token: dict = Depends(verify_bearer_token)):
    try:
        from backend.services.firebase_svc import get_db, DAILY_LIMIT
    except ModuleNotFoundError:
        from services.firebase_svc import get_db, DAILY_LIMIT
    from datetime import datetime, timezone
    uid = _decoded_token.get("uid", "unknown")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    db = get_db()
    used = 0
    if db:
        try:
            doc = db.collection("rate_limits").document(f"{uid}_{today}").get()
            if doc.exists:
                used = doc.to_dict().get("count", 0)
        except Exception:
            pass
    return {"used": used, "limit": DAILY_LIMIT, "remaining": max(0, DAILY_LIMIT - used)}


# 8️⃣ Download Local Report
@app.get("/report")
def download_report(filename: str):
    # Block traversal attempts and limit access to files inside uploads root.
    safe_filename = os.path.basename(filename)
    if not safe_filename or safe_filename != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    uploads_root = Path(UPLOAD_DIR).resolve()
    file_path = (uploads_root / safe_filename).resolve()

    if uploads_root not in file_path.parents:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        str(file_path),
        media_type="application/octet-stream",
        filename=safe_filename
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    reload = os.environ.get("ENV", "development").lower() == "development"
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)
