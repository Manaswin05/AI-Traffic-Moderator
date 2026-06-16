# K-Means Quick Reference Card

## 🚀 Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py

# Visit
http://localhost:5000
```

---

## 🎯 Core Concepts

### Input to K-Means
```python
vehicle_count = 12  # Just a number!
```

### Output from K-Means
```python
cluster = 1           # 0, 1, or 2
density = "MEDIUM"    # LOW, MEDIUM, or HIGH
```

---

## ⚙️ Configuration

```python
MIN_SAMPLES = 20              # Start training
RETRAIN_INTERVAL = 150        # Retrain frequency
MAX_DATA_SIZE = 200          # Memory limit
```

**Memory footprint:** ~7 KB (negligible!)

---

## 📊 Timeline

```
0min    10min    20min    30min    40min
 ├────────┼────────┼────────┼────────┤
Train  Retrain  Retrain  Retrain  Retrain
70%     80%      87%      91%      93%
```

---

## 🔌 API Endpoints

### Traffic Status
```bash
GET /traffic_status
```

### Model Info
```bash
GET /model_info
```

### Manual Train
```bash
POST /train_model
```

---

## 📝 Logs to Watch

```
✓ K-means trained | Centers: [2.5, 7.8, 16.2]
✓ Model saved successfully
✓ Model loaded | Centers: [2.5, 7.8, 16.2]
```

---

## 🎨 Video Overlay

```
Signal: GREEN
Vehicles: 15
AI Density: HIGH
Cluster: 2
```

---

## 💾 Memory (Render 512MB)

```
Total Used:  ~390 MB
Free Buffer: ~122 MB ✅
```

---

## ✅ Quick Test

```bash
# Check model status
curl http://localhost:5000/model_info

# Expected: trained: true
```

---

## 🛡️ Fallback

If K-means fails → Simple rules automatically

---

## 📚 Full Docs

- **KMEANS_README.md** - Complete guide
- **RENDER_DEPLOYMENT.md** - Deploy guide
- **TESTING_KMEANS.md** - Test procedures
- **KMEANS_SUMMARY.md** - Overview
- **VISUAL_COMPARISON.md** - If-else vs K-means
- **MEMORY_COMPARISON.md** - Memory analysis

---

## 🎯 Key Difference

### Before
```python
if vehicle_count >= 10:
    signal = "green"
```

### After
```python
cluster, density = kmeans.classify(vehicle_count)
if density == "HIGH":
    signal = "green"
```

**Learns instead of guessing!** 🧠
