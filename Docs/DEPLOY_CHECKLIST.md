# 🚀 Render Deployment Checklist

## Pre-Deployment (Local)

### 1. Build React Frontend
```bash
npm install
npm run build
```
**Verify:** `dist/` folder created with React build

---

### 2. Test Locally
```bash
python app.py
```
**Verify:** 
- App runs on http://localhost:5000
- Video feed works
- API endpoints respond
- K-means model trains

---

### 3. Commit All Changes
```bash
git add .
git commit -m "Production ready for Render deployment"
git push origin main
```

**Verify:** All files pushed except:
- ❌ `models/*.pt` (gitignored)
- ❌ `models/*.pkl` (gitignored)
- ❌ `node_modules/` (gitignored)
- ❌ `.venv/` (gitignored)
- ✅ `dist/` folder (React build)
- ✅ `requirements.txt`
- ✅ `package.json`
- ✅ `render.yaml`
- ✅ `Procfile`
- ✅ `build.sh`

---

## Render Setup

### 4. Create Web Service

**Settings:**
- **Name:** `ai-traffic-moderator`
- **Region:** Oregon (US West) or closest
- **Branch:** `main`
- **Environment:** Python 3
- **Build Command:** `chmod +x build.sh && ./build.sh`
- **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120`
- **Plan:** Free

---

### 5. Environment Variables (Optional)

Add in Render dashboard if needed:

| Key | Value |
|-----|-------|
| `VIDEO_SOURCE` | `demo_traffic.mp4` |
| `PYTHONUNBUFFERED` | `1` |

---

## Post-Deployment

### 6. Monitor Build Logs

Watch for:
```
✓ Building React frontend...
✓ Installing Python dependencies...
✓ Downloading YOLOv8n model...
✓ K-means trained | Centers: [3.2, 8.9, 18.1]
✓ Service is live!
```

**Expected build time:** 5-7 minutes

---

### 7. Test Production Endpoints

```bash
# Replace with your Render URL
RENDER_URL="https://ai-traffic-moderator.onrender.com"

# Test API
curl $RENDER_URL/traffic_status
curl $RENDER_URL/model_info

# Visit in browser
open $RENDER_URL
```

**Verify:**
- ✅ Traffic status returns JSON
- ✅ Model info shows trained: true
- ✅ React dashboard loads
- ✅ Video feed streams
- ✅ AI density displays

---

### 8. Monitor Performance

**Check Render Dashboard:**
- Memory usage: ~390 MB / 512 MB ✅
- CPU usage: ~30-40% ✅
- Response time: <200ms ✅
- No errors in logs ✅

---

## Quick Commands

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt
npm install

# Build frontend
npm run build

# Run locally
python app.py
```

### Git Workflow
```bash
# Make changes
git add .
git commit -m "Description"
git push origin main
# Render auto-deploys! ✅
```

### Troubleshooting
```bash
# View logs
# Go to Render dashboard → Logs tab

# Manual redeploy
# Go to Render dashboard → Manual Deploy

# Rollback
# Go to Render dashboard → Events → Rollback
```

---

## 📊 Expected Results

### Memory Usage
```
Component          Memory
──────────────────────────
YOLOv8n model      150 MB
Flask + OpenCV     130 MB
Python + libs       70 MB
scikit-learn        20 MB
K-means             ~7 KB
Buffer             120 MB
──────────────────────────
TOTAL             ~390 MB
FREE              ~122 MB ✅
```

### Response Times
```
Endpoint              Time
──────────────────────────
/traffic_status      <50ms
/model_info          <50ms
/video_feed         ~67ms/frame (15 FPS)
React app load       <2s
```

### Build Time
```
Phase                Time
──────────────────────────
Clone repo           10s
Install Node deps    60s
Build React          30s
Install Python deps  120s
Download YOLO        30s
Start service        20s
──────────────────────────
TOTAL               ~5min
```

---

## ✅ Success Criteria

Your deployment is successful when:

- [ ] Build completes without errors
- [ ] Service shows "Live" status
- [ ] Health check passes (green)
- [ ] `/traffic_status` returns JSON
- [ ] `/model_info` shows `trained: true`
- [ ] React dashboard loads in browser
- [ ] Video feed streams at ~15 FPS
- [ ] AI density classification works
- [ ] Memory usage < 400 MB
- [ ] No errors in logs

---

## 🆘 Common Issues & Solutions

### Issue: Build Fails
**Solution:** Check build logs, ensure all dependencies in requirements.txt

### Issue: Out of Memory
**Solution:** Memory usage is optimized. If issues persist, lower YOLO resolution

### Issue: Service Won't Start
**Solution:** Check start command, ensure PORT environment variable is used

### Issue: React Build Missing
**Solution:** Run `npm run build` locally first, commit `dist/` folder

### Issue: Model Download Fails
**Solution:** Wait for auto-retry, Ultralytics downloads automatically

---

## 📚 Full Documentation

- **Setup Guide:** `Docs/RENDER_SETUP_GUIDE.md`
- **Memory Details:** `Docs/RENDER_DEPLOYMENT.md`
- **Testing Guide:** `Docs/TESTING_KMEANS.md`
- **K-means FAQ:** `Docs/KMEANS_SUMMARY.md`
- **Model FAQ:** `Docs/YOLO_MODEL_FAQ.md`

---

## 🎉 Ready to Deploy!

**Your project is production-ready!**

1. Commit and push to GitHub
2. Create Render web service
3. Wait for build to complete
4. Test your live app!

**Expected URL:** `https://ai-traffic-moderator.onrender.com`

**Good luck!** 🚀
