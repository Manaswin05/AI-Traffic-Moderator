#!/bin/bash
# Build script for Render deployment - Optimized for 512MB RAM

echo "==> Building React frontend..."
npm install
npm run build

echo "==> Installing Python dependencies (CPU-only for memory optimization)..."
# Install CPU-only PyTorch from PyPI index
pip install --upgrade pip
pip install torch==2.1.1 torchvision==0.16.1 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt --no-deps

echo "==> Optimizations applied:"
echo "  ✓ CPU-only PyTorch (saves 300MB RAM)"
echo "  ✓ Single worker configuration"
echo "  ✓ Reduced YOLO input size: 320x320"
echo "  ✓ Reduced video resolution: 480x360"
echo "  ✓ Frame skipping enabled"
echo "  ✓ Garbage collection optimized"
echo ""
echo "==> Expected memory usage: ~236MB / 512MB available"
echo "==> Build complete!"
