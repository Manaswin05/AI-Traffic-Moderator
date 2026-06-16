#!/bin/bash
# Build script for Render deployment

echo "==> Building React frontend..."
npm install
npm run build

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Build complete!"
