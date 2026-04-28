# Android App Deployment Guide

This guide will help you deploy the FastAPI backend to Render and connect your Android app to it for full end-to-end functionality.

## Prerequisites
- GitHub account (already set up)
- Render account (free tier available at https://render.com)
- Google Gemini API key
- Cloudinary credentials (for image uploads)

## Step 1: Deploy Backend to Render

### Option A: Using render.yaml Blueprint (Recommended)

1. Go to **[Render Dashboard](https://dashboard.render.com)**
2. Click **New** → **Web Service**
3. Select **Deploy from Git**
4. Paste repository URL: `https://github.com/deeperzz8356/meediseen-backend.git`
5. Click **Connect**
6. Fill in these settings:
   - **Name:** `mediseen-api-backend` (or any unique name)
   - **Environment:** Docker
   - **Plan:** Free
   - **Branch:** `main`

7. Click **Deploy** and wait for the Render settings dialog
8. The render.yaml will be auto-detected. Click **Update Fields** to proceed.

### Option B: Manual Web Service Creation

If render.yaml is not detected:

1. Manually set these environment variables in Render:
   - `APP_ENV` = `production`
   - `ALLOWED_ORIGINS` = `capacitor://localhost,capacitor://app,file://,https://your-frontend.onrender.com`
   - `GEMINI_API_KEY` = (get from [Google AI Studio](https://aistudio.google.com))
   - `CLOUDINARY_NAME` = (from Cloudinary dashboard)
   - `CLOUDINARY_KEY` = (from Cloudinary)
   - `CLOUDINARY_SECRET` = (from Cloudinary)
   - `PORT` = `10000`

2. Build Command: (leave blank - uses Dockerfile)
3. Start Command: (leave blank - uses Dockerfile)

4. Click **Create Web Service**

## Step 2: Get Your Backend URL

After deployment completes (3-5 minutes):

1. Open your Render service dashboard
2. Copy the service URL from the top
   - Example: `https://mediseen-api-backend.onrender.com`
3. **Save this URL** - you'll need it next

## Step 3: Verify Backend is Working

Test the deployed backend:

```powershell
# Should return FastAPI OpenAPI docs (JSON)
curl https://YOUR_RENDER_URL/openapi.json

# Should show /diagnose endpoint available
curl https://YOUR_RENDER_URL/docs
```

If both return JSON/HTML with FastAPI docs, your backend is working correctly.

## Step 4: Update Android App Configuration

### Edit frontend/.env

1. Open `frontend/.env` in your editor
2. Find this line:
   ```
   NEXT_PUBLIC_API_URL=https://YOUR_RENDER_BACKEND_URL.onrender.com
   ```
3. Replace with your actual Render backend URL:
   ```
   NEXT_PUBLIC_API_URL=https://mediseen-api-backend.onrender.com
   ```

## Step 5: Rebuild Android App

Run these commands in order:

```powershell
# Go to frontend directory
cd frontend

# Build the Next.js static export
npm run build

# Sync Capacitor with the new build
npx cap sync android

# Go to Android build directory
cd android

# Clean and build the release APK
./gradlew.bat clean assembleRelease
```

The new APK will be at: `frontend/android/app/build/outputs/apk/release/app-release.apk`

## Step 6: Install and Test on Your Phone

1. Transfer the APK to your phone or use:
   ```powershell
   cd frontend/android
   ./gradlew.bat installDebug
   ```

2. Open the MediSeen app on your phone

3. Upload a chest X-ray image with symptoms

4. Expected flow:
   - App sends image + symptoms to: `https://YOUR_RENDER_URL/diagnose`
   - Backend processes with Gemini AI
   - Heatmap and diagnosis returned
   - App displays results with explanation

## Troubleshooting

### "Failed to fetch" error on Android

**Cause:** App is pointing to wrong backend URL

**Fix:**
1. Check `frontend/.env` has correct `NEXT_PUBLIC_API_URL`
2. Verify the Render backend URL is accessible: `curl https://your-url/docs`
3. Rebuild APK and reinstall

### Backend returns 405 Method Not Allowed

**Cause:** App is hitting the wrong service (frontend instead of backend)

**Fix:**
1. Confirm you're using the Render backend service URL (not frontend)
2. Test: `curl https://your-url/openapi.json` should return JSON, not HTML
3. Update `.env` and rebuild APK

### Image upload fails

**Cause:** Cloudinary credentials missing or invalid

**Fix:**
1. Get valid Cloudinary credentials from https://cloudinary.com
2. Set in Render dashboard:
   - `CLOUDINARY_NAME`
   - `CLOUDINARY_KEY`
   - `CLOUDINARY_SECRET`
3. Redeploy the backend on Render

### Gemini API returns error

**Cause:** GEMINI_API_KEY missing or invalid

**Fix:**
1. Get free API key from [Google AI Studio](https://aistudio.google.com)
2. Set `GEMINI_API_KEY` in Render environment variables
3. Redeploy

## Full End-to-End Testing Checklist

- [ ] Backend deployed on Render
- [ ] Backend URL responds to `/openapi.json` with FastAPI docs
- [ ] `NEXT_PUBLIC_API_URL` updated in frontend/.env
- [ ] Frontend rebuilt: `npm run build`
- [ ] Capacitor synced: `npx cap sync android`
- [ ] Android APK rebuilt: `./gradlew.bat clean assembleRelease`
- [ ] APK installed on phone
- [ ] App opens without errors
- [ ] Image upload works
- [ ] Diagnosis returns from backend
- [ ] Heatmap and explanation displayed

## Support

For issues during deployment:

1. Check Render logs: Dashboard → Your Service → Logs
2. Check backend locally: `python -m uvicorn backend.main:app --port 8000`
3. Verify environment variables are set correctly in Render
4. Ensure GitHub repo has latest code: `git push origin main`

---

**You're all set!** Once the Android app successfully uploads an image and receives a diagnosis from your Render backend, the system is fully functional.
