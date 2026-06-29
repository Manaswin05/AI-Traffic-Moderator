# ── Stage 1: Build React frontend ──────────────────────────────────────────
FROM node:18-slim AS frontend-builder

WORKDIR /app

# Copy package files and install deps
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY vite.config.js ./
COPY src/ ./src/
COPY index.html ./
RUN npm run build

# ── Stage 2: Python / Flask runtime ────────────────────────────────────────
FROM python:3.11-slim

# Install system libs required by OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Python deps and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py ./
COPY models/ ./models/

# Copy built React frontend from stage 1
COPY --from=frontend-builder /app/dist ./dist

# Hugging Face Spaces requires port 7860
# The gunicorn start command reads $PORT; we set it here.
ENV PORT=7860

# Expose the port HF Spaces expects
EXPOSE 7860

# Start gunicorn (same command as Render Procfile)
CMD ["gunicorn", "app:app", \
     "--bind", "0.0.0.0:7860", \
     "--workers", "1", \
     "--threads", "2", \
     "--timeout", "120", \
     "--log-level", "info"]
