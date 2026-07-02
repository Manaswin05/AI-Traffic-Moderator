# Deploying Any Web App to Hugging Face Spaces with Docker

A complete guide on how to deploy a custom frontend + AI backend (Flask, FastAPI, etc.)
to Hugging Face Spaces — without being limited to Gradio or Streamlit.

---

## Why Docker Mode?

By default, HF Spaces only supports Gradio and Streamlit UIs. But HF also supports a
**Docker SDK mode** that lets you run literally anything inside a container:

| SDK | Restriction |
|-----|-------------|
| `gradio` | Must use Gradio UI |
| `streamlit` | Must use Streamlit UI |
| `static` | Plain HTML/CSS/JS only |
| `docker` | **No restrictions — full control** |

With `sdk: docker`, HF builds and runs your `Dockerfile`. You get:
- Any backend: Flask, FastAPI, Django, Express, etc.
- Any frontend: React, Vue, Angular, plain HTML
- Any AI model: YOLO, PyTorch, TensorFlow, HuggingFace models
- Full filesystem, environment variables, and port control

---

## The Two Requirements

No matter what your app does, you only need two things:

### 1. A `Dockerfile` in the repo root

This tells HF how to build and run your app.

### 2. HF Spaces front-matter in `README.md`

```yaml
---
title: Your App Name
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---
```

The critical fields are `sdk: docker` and `app_port: 7860`.
HF **always** expects your app to listen on port **7860**.

---

## Dockerfile Structure (Flask + React Example)

This is the exact pattern used for the AI Traffic Moderator project.

```dockerfile
# ── Stage 1: Build React frontend ──────────────────────────────────────────
FROM node:18-slim AS frontend-builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY vite.config.js ./
COPY src/ ./src/
COPY index.html ./
RUN npm run build

# ── Stage 2: Python / Flask runtime ────────────────────────────────────────
FROM python:3.11-slim

# System libs for OpenCV (remove if not using OpenCV)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY models/ ./models/

# Copy built React frontend from Stage 1
COPY --from=frontend-builder /app/dist ./dist

# HF Spaces requires port 7860
ENV PORT=7860
EXPOSE 7860

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860", "--workers", "1", "--threads", "2", "--timeout", "120"]
```

**Key points:**
- Multi-stage build keeps the final image small (no Node.js in production image)
- Flask serves the built React `dist/` folder as static files
- Port is hardcoded to `7860` — HF requires this

---

## Flask: Serving React from the Same Server

Your Flask `app.py` needs to serve the React build output:

```python
from flask import Flask, send_from_directory
import os

STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'dist')
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='')

# Serve React SPA for all non-API routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')
```

This way:
- `/api/...` routes are handled by Flask
- Everything else serves `index.html` (React Router takes over)

---

## Handling Large Files (Models, Videos)

HF rejects binary files pushed via regular git. Use **Git LFS** for anything large:

```bash
# Install Git LFS
git lfs install

# Track file types
git lfs track "*.pt"      # PyTorch models
git lfs track "*.pkl"     # Pickle files
git lfs track "*.mp4"     # Videos
git lfs track "*.pptx"    # PowerPoint files

# Commit .gitattributes first
git add .gitattributes
git add models/yolov8n.pt
git commit -m "Add model via LFS"
git push
```

HF Spaces supports Git LFS files up to **5 GB** per file.

---

## Setting Environment Variables

You can set env vars in three ways:

### Option 1 — Hardcode in Dockerfile (for non-secrets)
```dockerfile
ENV VIDEO_SOURCE=/app/demo_traffic.mp4
ENV MY_SETTING=production
```

### Option 2 — HF Spaces UI (for secrets/tokens)
Space → **Settings** → **Variables and secrets** → Add variable

### Option 3 — README front-matter (limited support)
```yaml
---
sdk: docker
app_port: 7860
---
```

---

## Pushing to HF Spaces via Git

HF Spaces is a git repo. You push to it like any remote:

```bash
# Add HF Space as a remote
git remote add space https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME

# Push (use your HF write token for authentication)
git remote set-url space https://YOUR_USERNAME:hf_YOUR_TOKEN@huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
git push space main
```

### Getting a Write Token
1. Go to https://huggingface.co/settings/tokens
2. Click **New token**
3. Select **Fine-grained**
4. Check **"Write access to contents/settings of all repos"**
5. Save and copy the token

### Force Push (when histories don't match)
If HF has an existing Space with unrelated history:
```bash
git push space main --force
```

---

## Free Tier Resources

HF Spaces free tier (Docker SDK) gives you:

| Resource | Amount |
|----------|--------|
| CPU | 2 vCPUs |
| RAM | 16 GB |
| Storage | 50 GB |
| Sleep after inactivity | ~48 hours |

The 16 GB RAM is enough to run YOLOv8, PyTorch models, and a web server simultaneously.

**Limitation:** Spaces go to sleep after ~48 hours of no traffic. The next visitor wakes it up (takes ~1-2 min to boot). Paid plans can keep it always-on.

---

## Template for Any New AI + Web Project

Here's a minimal starting point you can copy for any future project:

**File structure:**
```
my-project/
├── Dockerfile
├── README.md          ← must have HF front-matter
├── app.py             ← Flask/FastAPI backend
├── requirements.txt
├── models/            ← AI models (use LFS for .pt files)
├── src/               ← React/Vue source
├── package.json
└── index.html
```

**README.md front-matter:**
```yaml
---
title: My AI Project
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---
```

**Dockerfile (minimal):**
```dockerfile
FROM node:18-slim AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY --from=frontend /app/dist ./dist
ENV PORT=7860
EXPOSE 7860
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:7860"]
```

---

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `You are not authorized to push` | Token has no write permission | Recreate token with Write access checked |
| `Binary files rejected` | Large files pushed without LFS | Use `git lfs track` for `.pt`, `.mp4`, `.pkl` |
| `not found` in COPY step | File not in repo/build context | Make COPY optional with glob: `COPY file.mp4* ./` |
| `ERR_CONNECTION_CLOSED` | Space is sleeping or rebuilding | Wait 2-5 min and refresh |
| App loads but API calls fail | Port mismatch | Ensure your app binds to `0.0.0.0:7860` |

---

## Summary

1. Add `sdk: docker` + `app_port: 7860` to `README.md` front-matter
2. Write a `Dockerfile` that builds your app and exposes port `7860`
3. Use Git LFS for any binary files over a few MB
4. Create a HF token with Write access
5. `git push` to the HF Space remote

That's it. Any stack, any framework, any AI model — fully deployable on HF Spaces for free.
