# PyTorch → ONNX Runtime Migration

## Why This Change

The Render free tier provides **512 MB RAM**. The original stack used PyTorch at
runtime, which consumed the majority of that budget before the app even handled
a single request.

| Component | Before (PyTorch) | After (ONNX Runtime) |
|---|---|---|
| Inference library disk size | ~800 MB | ~50 MB |
| Inference library RAM at startup | ~200 MB | ~30 MB |
| ultralytics at runtime | ~100 MB | removed |
| Estimated total runtime RAM | ~380 MB | ~130 MB |
| Headroom on 512 MB tier | ~130 MB | **~380 MB** |

---

## How It Works

### Build Time (Render build step)
1. `build.sh` installs PyTorch + ultralytics temporarily.
2. Exports `models/yolov8n.pt` → `models/yolov8n.onnx` using:
   ```
   model.export(format="onnx", imgsz=320, simplify=True)
   ```
3. PyTorch and ultralytics are **not** added to `requirements.txt` — they exist
   only during the build container and are discarded before the dyno starts.

### Runtime
- `onnxruntime-cpu` loads `yolov8n.onnx` directly.
- Inference pipeline (`detect_vehicles()` in `app.py`):
  1. Resize frame to 320×320
  2. Normalize pixels to `[0, 1]`
  3. Transpose to `(1, 3, 320, 320)` — ONNX/NCHW format
  4. Run `session.run()`
  5. Parse output shape `(1, 84, num_boxes)` → filter by confidence + vehicle class IDs

### K-Means (unchanged)
The K-means classifier is **completely unaffected** by this change. It operates
on vehicle counts (integers) produced after ONNX inference and has no dependency
on PyTorch or ultralytics.

```
ONNX Inference → vehicle_count (int) → K-Means → LOW / MEDIUM / HIGH → Signal logic
```

---

## ONNX Output Format

YOLOv8 ONNX output: `(1, 84, num_boxes)`

- Rows 0–3: `cx, cy, w, h` (normalized to input size)
- Rows 4–83: class confidence scores for 80 COCO classes

Vehicle class IDs used:
| ID | Label |
|---|---|
| 2 | car |
| 3 | motorcycle |
| 5 | bus |
| 7 | truck |

Confidence threshold: `0.35`

---

## Files Changed

| File | Change |
|---|---|
| `app.py` | Removed `torch`, `ultralytics` imports. Added `onnxruntime`. Rewrote `load_onnx_model()` and `detect_vehicles()`. |
| `requirements.txt` | Removed `torch`, `torchvision`, `ultralytics`. Added `onnxruntime==1.17.1`, `werkzeug==3.0.1`. |
| `build.sh` | Added one-time ONNX export step. Removed runtime PyTorch install. |

---

## Local Development

If you want to run locally without the build step:

```bash
# One-time: export the model
pip install ultralytics torch
python -c "
from ultralytics import YOLO
model = YOLO('models/yolov8n.pt')
model.export(format='onnx', imgsz=320, simplify=True)
"

# Then install only runtime deps
pip install onnxruntime opencv-python-headless flask flask-cors numpy scikit-learn
python app.py
```

---

## Rollback

To revert to PyTorch, checkout the previous commit on `main` before this PR was merged.
The `yolov8n.pt` file remains in `models/` and is untouched.
