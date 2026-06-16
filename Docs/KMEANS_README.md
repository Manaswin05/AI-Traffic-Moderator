# K-Means Traffic Classification System

## Overview

This project now uses **K-means clustering** machine learning algorithm to intelligently classify traffic density and control traffic signals, replacing the simple if-else conditions.

## How It Works

### 1. **Instant Operation with Seed Data**
- System starts with pre-seeded realistic traffic patterns
- No waiting period - K-means works from second one!
- Seed data: Low (1-5), Medium (7-12), High (15-25) vehicles

### 2. **K-Means Clustering**
The algorithm creates **3 clusters** representing:
- **Cluster 0**: Low traffic (few vehicles)
- **Cluster 1**: Medium traffic (moderate vehicles)
- **Cluster 2**: High traffic (many vehicles)

### 3. **Continuous Learning**
- Collects real vehicle count data as it runs
- Stores last **200 readings** in memory (only ~1.6 KB!)
- **Memory-optimized for Render free tier (512MB RAM)**
- Uses efficient `deque` structure with automatic size limits

### 4. **Smart Retraining**
- Retrains every **150 new samples** (~10-15 minutes)
- Time-based safety net: every 3 hours minimum
- Training happens in background without interrupting video
- Model auto-saves to `models/traffic_kmeans.pkl`
- Persists across restarts

### 5. **Real-Time Classification**
Every frame, the model:
- Takes current vehicle count as input
- Classifies traffic into low/medium/high density
- Uses sorted cluster centers (always 0=low, 1=medium, 2=high)
- Falls back to simple rules if model isn't ready

### 6. **AI-Driven Signal Logic**
Based on K-means classification (not fixed thresholds!):
- **Low Traffic**: Short red lights (10s) to keep flow moving
- **Medium Traffic**: Yellow signal (8s) for transition
- **High Traffic**: Long green lights (20s) to clear congestion

## Advantages Over If-Else

### Traditional Approach (Before)
```python
if vehicle_count >= 10:
    signal = "green"
elif vehicle_count >= 5:
    signal = "yellow"
else:
    signal = "red"
```
**Problems:**
- Fixed thresholds don't adapt to different road conditions
- No learning from historical patterns
- Same rules for all times of day

### K-Means Approach (Now)
```python
cluster, density = classify_traffic(vehicle_count)
signal, timer = determine_signal_from_density(density)
```
**Benefits:**
- ✅ **Adaptive**: Learns from actual traffic patterns
- ✅ **Intelligent**: Discovers natural groupings in data
- ✅ **Flexible**: Adjusts to different road conditions
- ✅ **Data-driven**: Decisions based on real observations
- ✅ **Scalable**: Can incorporate more features (time, weather, etc.)

## API Endpoints

### Get Traffic Status
```
GET /traffic_status
```
Returns:
```json
{
  "traffic_light": "green",
  "vehicle_count": 15,
  "traffic_density": "high",
  "cluster": 2,
  "model_trained": true,
  "data_collected": 87
}
```

### Get Model Information
```
GET /model_info
```
Returns:
```json
{
  "trained": true,
  "samples_collected": 187,
  "cluster_centers": [2.5, 7.8, 16.2],
  "samples_since_retrain": 37,
  "next_retrain_in": 113
}
```

### Manual Training (Optional)
```
POST /train_model
```
Forces model retraining with current data

## Visual Indicators

The video feed now displays:
- **Signal**: Current traffic light state
- **Vehicles**: Real-time vehicle count
- **AI Density**: Classification (LOW/MEDIUM/HIGH)
- **Cluster**: Which cluster the current state belongs to

## Dashboard Enhancements

New statistics cards show:
- **AI Density**: Color-coded traffic classification
- **Cluster**: Current cluster assignment
- **Model Status**: Whether the AI model is trained
- **Samples Collected**: Training data progress
- **Cluster Centers**: Learned traffic patterns

## Installation

1. Install the new dependency:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
```

3. The system will:
   - Initialize or load existing K-means model
   - Start collecting traffic data
   - Automatically train after 30+ samples
   - Begin intelligent traffic classification

## Future Enhancements

The K-means approach opens doors for:
- **Multi-feature clustering**: Add time of day, day of week, weather
- **Multiple intersections**: Learn patterns for different locations
- **Predictive modeling**: Anticipate traffic before it builds up
- **Real-time retraining**: Continuously improve with new data
- **Anomaly detection**: Identify unusual traffic patterns

## Technical Details

- **Algorithm**: K-means clustering (sklearn)
- **Features**: Vehicle count (expandable to multi-feature)
- **Clusters**: 3 (low, medium, high) - automatically sorted
- **Memory footprint**: ~1.6 KB for data, ~5 KB for model
- **Training data**: Last 200 observations (deque with maxlen)
- **Minimum samples**: 20 for initial training
- **Retrain interval**: Every 150 samples (~10-15 minutes)
- **Model persistence**: Saved as pickle to `models/traffic_kmeans.pkl`
- **Fallback**: Simple rules if model isn't ready
- **Deployment**: Optimized for Render free tier (512MB RAM)

## Conclusion

By replacing simple if-else conditions with K-means clustering, the traffic control system now makes intelligent, data-driven decisions that adapt to real-world traffic patterns. The AI learns from observations and continuously improves its classification accuracy.
