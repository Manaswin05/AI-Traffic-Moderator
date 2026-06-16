# Testing K-Means Implementation

## Quick Start Test

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python app.py
```

### Expected Output:
```
✓ Model loaded | Centers: [2.5, 7.8, 16.2]  
  OR
○ No saved model found - will train from seed data
✓ K-means trained | Centers: [3.2, 8.9, 18.1]

==================================================
AI Traffic Control System - Starting
==================================================
Camera/Video status: Ready (or placeholder mode)
Flask server: http://localhost:5000
==================================================
```

---

## API Testing

### Test 1: Check Traffic Status
```bash
curl http://localhost:5000/traffic_status
```

**Expected Response:**
```json
{
  "traffic_light": "red",
  "vehicle_count": 5,
  "traffic_density": "LOW",
  "cluster": 0,
  "model_trained": true,
  "samples_collected": 25,
  "cluster_centers": [3.2, 8.9, 18.1]
}
```

**What to Verify:**
- ✅ `model_trained: true` (model is working)
- ✅ `traffic_density` matches vehicle count
- ✅ `cluster_centers` are sorted (low to high)
- ✅ `samples_collected` is increasing

---

### Test 2: Check Model Information
```bash
curl http://localhost:5000/model_info
```

**Expected Response:**
```json
{
  "trained": true,
  "samples_collected": 25,
  "cluster_centers": [3.2, 8.9, 18.1],
  "samples_since_retrain": 5,
  "next_retrain_in": 145
}
```

**What to Verify:**
- ✅ `trained: true`
- ✅ `samples_since_retrain` is counting up
- ✅ `next_retrain_in` is counting down

---

### Test 3: Manual Training
```bash
curl -X POST http://localhost:5000/train_model
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Model retrained successfully",
  "stats": {
    "trained": true,
    "samples_collected": 25,
    "cluster_centers": [3.2, 8.9, 18.1],
    "samples_since_retrain": 0,
    "next_retrain_in": 150
  }
}
```

**What to Verify:**
- ✅ `samples_since_retrain` reset to 0
- ✅ `next_retrain_in` reset to 150
- ✅ Console shows: `✓ K-means trained | Centers: ...`

---

## Visual Testing (Browser)

### 1. Open Video Feed
Navigate to: `http://localhost:5000`

**What to Look For:**

**On Video Frame:**
- Signal: RED/YELLOW/GREEN (color-coded)
- Vehicles: X (count)
- AI Density: LOW/MEDIUM/HIGH (color-coded)
- Cluster: 0/1/2

**Verify:**
- ✅ Density colors match traffic:
  - LOW = Green
  - MEDIUM = Yellow
  - HIGH = Red
- ✅ Cluster matches density (0=LOW, 1=MED, 2=HIGH)
- ✅ Signal timing changes based on density

---

## Classification Testing

Test if K-means correctly classifies different traffic levels:

### Test Scenarios

| Vehicle Count | Expected Cluster | Expected Density | Signal Response |
|---------------|------------------|------------------|-----------------|
| 0-5 | 0 | LOW | Short red (10s) |
| 6-10 | 1 | MEDIUM | Yellow (8s) |
| 11+ | 2 | HIGH | Long green (20s) |

**Note:** These are approximate - K-means learns actual patterns from your data!

---

## Monitoring Logs

### What to Watch For

#### Successful Operation
```
✓ K-means trained | Centers: [2.5, 7.8, 16.2]
✓ Model saved successfully
SUCCESS: Using video file: demo_traffic.mp4
  OR
SUCCESS: Camera 0 opened. Shape: (480, 640, 3)
```

#### Retraining Events
```
✓ K-means trained | Centers: [2.8, 8.2, 17.1]
✓ Model saved successfully
```

**Expected:** Every ~150 samples (10-15 minutes)

#### Fallback Activation (Rare)
```
✗ Classification error: ...
```

**Note:** System automatically uses simple rules as fallback

---

## Model Persistence Testing

### Test 4: Restart Application

1. **Run app and let it collect data:**
   ```bash
   python app.py
   # Wait 2-3 minutes
   # Ctrl+C to stop
   ```

2. **Check that model was saved:**
   ```bash
   ls models/
   # Should see: traffic_kmeans.pkl
   ```

3. **Restart application:**
   ```bash
   python app.py
   ```

4. **Verify model loaded:**
   ```
   ✓ Model loaded | Centers: [2.5, 7.8, 16.2]
   ```

**What to Verify:**
- ✅ Model loads automatically
- ✅ Cluster centers are same as before restart
- ✅ No need to retrain from scratch

---

## Memory Monitoring

### On Linux/Mac:
```bash
# Monitor memory while running
ps aux | grep python
```

### On Windows:
```powershell
# Task Manager or:
Get-Process python | Select-Object Name, PM, WS
```

**Expected Memory:**
- **Startup:** ~230 MB
- **Running:** ~250 MB
- **Peak (training):** ~280 MB
- **Should stay under:** 350 MB

**If memory exceeds 400 MB:** Something is wrong!

---

## Performance Testing

### Frame Rate Test
Open browser console (F12) and run:
```javascript
let frames = 0;
setInterval(() => {
  console.log('FPS:', frames);
  frames = 0;
}, 1000);

// Count frames
const img = document.querySelector('img');
img.addEventListener('load', () => frames++);
```

**Expected:** 10-15 FPS

---

## Cluster Quality Testing

After collecting ~100 samples, check if clusters make sense:

### Test 5: Analyze Cluster Centers
```bash
curl http://localhost:5000/model_info | json_pp
```

**Good Clusters Example:**
```json
{
  "cluster_centers": [2.5, 8.3, 16.8]
}
```

**Analysis:**
- Low center (2.5): 2-5 vehicles
- Medium center (8.3): 6-12 vehicles  
- High center (16.8): 13+ vehicles
- ✅ Clear separation between clusters

**Bad Clusters Example:**
```json
{
  "cluster_centers": [5.1, 5.8, 6.2]
}
```

**Analysis:**
- ❌ All centers too close together
- ❌ Not enough traffic variation in data
- **Solution:** Collect more diverse samples

---

## Troubleshooting Tests

### Issue: Model Not Training

**Check 1:** Sample count
```bash
curl http://localhost:5000/model_info
```
- Need at least 20 samples
- Check `samples_collected` value

**Check 2:** File permissions
```bash
ls -la models/
```
- Directory should exist
- Should have write permissions

**Check 3:** Dependencies
```bash
pip list | grep scikit-learn
```
- Should show: `scikit-learn==1.3.2`

---

### Issue: Wrong Classifications

**Symptoms:**
- High traffic classified as LOW
- Low traffic classified as HIGH

**Diagnosis:**
```bash
curl http://localhost:5000/model_info
```

Check cluster centers:
- If centers are [20, 25, 30]: Model only saw high traffic
- If centers are [1, 2, 3]: Model only saw low traffic

**Solution:**
1. Delete model: `rm models/traffic_kmeans.pkl`
2. Restart: `python app.py`
3. Fresh training with seed data

---

### Issue: Excessive Memory Usage

**Check:**
```python
# In app.py, verify:
MAX_DATA_SIZE = 200  # Should be 200, not 2000!
```

**Monitor deque size:**
```python
# Add temporary logging
print(f"Deque size: {len(kmeans_system.training_data)}")
```

**Expected:** Should never exceed 200

---

## Automated Test Script

Save as `test_kmeans.py`:

```python
import requests
import time

BASE_URL = "http://localhost:5000"

def test_endpoints():
    print("Testing K-means implementation...")
    
    # Test 1: Traffic status
    r = requests.get(f"{BASE_URL}/traffic_status")
    assert r.status_code == 200
    data = r.json()
    assert "traffic_density" in data
    assert "cluster" in data
    print("✅ Traffic status endpoint OK")
    
    # Test 2: Model info
    r = requests.get(f"{BASE_URL}/model_info")
    assert r.status_code == 200
    data = r.json()
    assert data["trained"] == True
    assert len(data["cluster_centers"]) == 3
    print("✅ Model info endpoint OK")
    
    # Test 3: Manual training
    r = requests.post(f"{BASE_URL}/train_model")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    print("✅ Manual training OK")
    
    # Test 4: Cluster ordering
    r = requests.get(f"{BASE_URL}/model_info")
    centers = r.json()["cluster_centers"]
    assert centers[0] < centers[1] < centers[2]
    print("✅ Clusters correctly sorted")
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_endpoints()
```

**Run:**
```bash
pip install requests
python test_kmeans.py
```

---

## Load Testing (Optional)

Test system under continuous load:

```python
import requests
import time

BASE_URL = "http://localhost:5000"

for i in range(200):
    r = requests.get(f"{BASE_URL}/traffic_status")
    print(f"Request {i+1}: {r.elapsed.total_seconds():.3f}s")
    time.sleep(0.1)  # 10 req/sec
```

**Expected:**
- Response time: <100ms
- No memory leaks
- Automatic retraining after 150 samples

---

## Success Criteria

Your K-means implementation is working correctly if:

✅ Model trains automatically from seed data  
✅ Classifications match traffic levels (LOW/MEDIUM/HIGH)  
✅ Cluster centers are properly sorted  
✅ Retraining happens every 150 samples  
✅ Model persists across restarts  
✅ Memory stays under 300 MB  
✅ API endpoints respond correctly  
✅ Video overlay shows AI density  
✅ Signal timing adapts to density  
✅ Fallback works if ML fails  

---

## Next Steps

Once basic testing passes:

1. **Deploy to Render** - Test in production environment
2. **Monitor logs** - Watch for retraining events
3. **Collect real data** - Let it run for a few hours
4. **Verify adaptation** - Check if clusters improve over time
5. **Test edge cases** - Very low/high traffic scenarios

**Your K-means system is production-ready!** 🚀
