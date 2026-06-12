# AI Traffic Control System 🚦

A modern AI-powered traffic signal control system that uses **YOLOv8** for real-time vehicle detection and dynamically manages traffic signals. Built with **React**, **Flask**, **OpenCV**, and **Ultralytics YOLO**.

![Traffic Control System](https://img.shields.io/badge/AI-Traffic%20Control-blue)
![React](https://img.shields.io/badge/React-18.2.0-61dafb)
![Flask](https://img.shields.io/badge/Flask-3.0.0-000000)
![Python](https://img.shields.io/badge/Python-3.11-3776ab)

## ✨ Features

- 🎯 **Real-time Vehicle Detection** - YOLOv8 powered detection for cars, motorcycles, buses, and trucks
- 🤖 **Unsupervised ML Traffic Control** - K-Means clustering for adaptive signal timing
- 🎛️ **Manual Training Controls** - Train or reset ML model on-demand via dashboard
- 📊 **Live Analytics Dashboard** - Real-time vehicle count graphs and statistics
- 🗺️ **Interactive Map View** - Traffic camera location visualization with Leaflet
- 📹 **Live Video Streaming** - Real-time camera feed with vehicle annotations
- 🧠 **Self-Learning System** - Automatically adapts to traffic patterns without manual tuning
- 🎨 **Modern UI** - Professional React-based interface with smooth animations
- 📱 **Responsive Design** - Works seamlessly on desktop and mobile devices

## 🛠️ Tech Stack

### Frontend
- **React 18.2.0** - Modern UI framework
- **React Router 6.20.0** - Client-side routing
- **Chart.js 4.4.0** - Real-time data visualization
- **React Leaflet 4.2.1** - Interactive maps with Leaflet 1.9.4
- **Axios 1.6.2** - HTTP client
- **Three.js 0.183.2** - 3D graphics library
- **Lenis 1.3.19** - Smooth scrolling
- **Vite 5.0.8** - Fast build tool and dev server

### Backend
- **Flask 3.0.0** - Python web framework
- **Flask-CORS 4.0.0** - Cross-origin resource sharing
- **OpenCV 4.8.1.78** (headless) - Video processing
- **YOLOv8 (Ultralytics 8.0.196)** - Object detection
- **PyTorch 2.1.1** - Deep learning framework
- **Scikit-learn 1.3.2** - K-Means clustering for adaptive traffic control
- **Gunicorn 21.2.0** - WSGI HTTP server for production
- **NumPy 1.26.2** - Numerical computing

## 📋 Prerequisites

- **Python 3.8+** (tested with Python 3.11)
- **Node.js 16+** and npm
- **Webcam** (for live detection) or a video file
- **Git**
- **2GB RAM** minimum (4GB+ recommended for smooth performance)
- **GPU** optional but recommended for better performance

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/AI-Traffic-Moderator.git
cd AI-Traffic-Moderator
```

### 2. Set Up Python Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Node.js Dependencies

```bash
npm install
```

### 5. Set Up YOLOv8 Model

The YOLOv8 nano model (`yolov8n.pt`) should be placed in the `models/` directory. It will be automatically downloaded by Ultralytics on first run if not present.

## 🎮 Running the Application

### Option 1: Run Both Servers with One Command (Recommended)

```bash
npm run dev
```

This will start both the Flask backend (port 5000) and Vite frontend (port 5173) concurrently.

### Option 2: Run Servers Separately

**Terminal 1: Start Flask Backend**

```bash
python app.py
```

The backend will run on `http://localhost:5000`

**Terminal 2: Start React Frontend**

```bash
vite
```

The frontend will run on `http://localhost:5173`

### Access the Application

Open your browser and navigate to:
```
http://localhost:5173
```

**Login:** Use any username and password (demo authentication)

## 🎥 Video Source Options

The application supports multiple video sources:

1. **Webcam (Default)**: Automatically detects available webcams (indexes 0, 1, 2)
2. **Video File**: Set environment variable `VIDEO_SOURCE` to your video file path
   ```bash
   # Windows
   set VIDEO_SOURCE=path/to/traffic_video.mp4
   python app.py
   
   # macOS/Linux
   export VIDEO_SOURCE=path/to/traffic_video.mp4
   python app.py
   ```
3. **Placeholder Mode**: If no camera or video is found, displays a placeholder with grid pattern

### 🎬 Demo with YouTube Videos

For demo/testing purposes without real traffic cameras:

1. Find a traffic monitoring video on YouTube (search "traffic cam live")
2. Start the application:
   ```bash
   npm run dev
   ```
3. Play the YouTube video in fullscreen or large window
4. Point your laptop camera at the screen
5. Navigate to the Dashboard
6. Watch the ML status indicator: "ML: LEARNING (X/15)"
7. **Option A**: Wait ~30 seconds for automatic training when 15 samples are collected
8. **Option B**: Use "🎯 Train Model Now" button for manual training (needs minimum 5 samples)
9. Once trained, observe how traffic lights adapt to the video's traffic patterns!

**Manual Training Controls:**
- **Train Model Now**: Manually trigger training before auto-training (needs ≥5 samples)
- **Reset & Start Fresh**: Clear all collected data and restart learning
- **ML Status Display**: Shows training progress and sample count

**Tip**: Use videos with varying traffic density (rush hour, light traffic) for better ML training.

## 📁 Project Structure

```
AI-Traffic-Moderator/
├── src/                          # React frontend source
│   ├── components/               # Reusable components
│   │   ├── Header.jsx           # Navigation header
│   │   └── TrafficLight.jsx     # Traffic signal component
│   ├── pages/                   # Page components
│   │   ├── Login.jsx            # Login page
│   │   ├── Dashboard.jsx        # Main dashboard
│   │   └── MapView.jsx          # Map view page
│   ├── App.jsx                  # Main app component
│   └── main.jsx                 # Entry point
├── models/                      # AI models
│   └── yolov8n.pt              # YOLOv8 nano model
├── Wireless type/               # Future wireless implementation
├── Docs/                        # Project documentation
├── app.py                       # Flask backend server
├── requirements.txt             # Python dependencies
├── package.json                 # Node.js dependencies
├── vite.config.js              # Vite configuration
└── README.md                    # This file
```

## 🤖 Unsupervised ML Approach

### K-Means Clustering for Adaptive Traffic Control

Instead of using fixed if-else rules, this system employs **K-Means clustering** (unsupervised learning) to automatically learn optimal traffic patterns:

#### How It Works

1. **Data Collection Phase** (0-15 observations)
   - System collects vehicle count data from real-time detection
   - Samples every 15 frames to speed up data collection
   - Operates using fallback rules during learning phase
   - Shows "ML: LEARNING (X/15)" status on video feed
   - **Takes ~30 seconds** to collect enough data for training

2. **Training Phase** (after 15+ observations)
   - K-Means algorithm identifies 3 natural clusters in traffic data
   - Clusters represent: Low, Medium, and High traffic density
   - Automatically determines optimal signal timing for each cluster
   - Shows "ML: TRAINED" status on video feed
   - **Happens automatically** after ~30 seconds of operation

3. **Prediction Phase** (ongoing)
   - Current vehicle count is classified into learned clusters
   - Green light duration adapts based on cluster characteristics:
     - **Low traffic cluster**: 15 seconds green
     - **Medium traffic cluster**: 20 seconds green
     - **High traffic cluster**: 30 seconds green
   - Proper signal transitions: Red → Green → Yellow → Red
   - Maintains 100-observation rolling window for continuous adaptation
   - Retrains periodically to adapt to changing traffic patterns

#### Advantages Over Rule-Based Systems

- ✅ **Self-calibrating**: No manual threshold tuning required
- ✅ **Adaptive**: Learns from actual traffic patterns at deployment location
- ✅ **Dynamic**: Continuously adapts to changing traffic conditions
- ✅ **Efficient**: Optimizes signal timing based on real data distribution
- ✅ **Scalable**: Can handle different traffic scenarios without reprogramming

#### Technical Details

```python
class AdaptiveTrafficController:
    """
    K-Means based adaptive traffic light controller
    - n_clusters: 3 (low, medium, high traffic)
    - history_size: 100 observations (rolling window)
    - min_samples: 30 (before initial training)
    """
```

**Cluster Mapping** (automatically learned):
- Cluster 0 (Low traffic) → Green 15s → Yellow 4s → Red 8s
- Cluster 1 (Medium traffic) → Green 20s → Yellow 4s → Red 8s
- Cluster 2 (High traffic) → Green 30s → Yellow 4s → Red 8s

The system automatically identifies which cluster represents which traffic level based on the average vehicle count in each cluster. Higher vehicle counts get longer green lights to clear traffic efficiently.

## 🎯 How It Works

1. **Video Capture** - Captures live video feed from webcam or video file
2. **Vehicle Detection** - YOLOv8 processes each frame to detect vehicles (cars, motorcycles, buses, trucks)
3. **Traffic Analysis** - Counts vehicles and feeds data to ML controller
4. **Unsupervised Learning** - K-Means clustering adaptively learns traffic patterns:
   - Collects historical vehicle count data (100 observations)
   - Trains after 30 samples to identify 3 traffic density clusters (low, medium, high)
   - Dynamically adjusts green light duration based on learned patterns
   - More vehicles = longer green light to clear traffic efficiently
   - Adapts to changing traffic conditions over time
5. **Signal Control** - ML-predicted green light timing with proper transitions:
   - **Red → Green**: Duration based on traffic cluster (15s-30s)
   - **Green → Yellow**: Always 4 seconds (transition warning)
   - **Yellow → Red**: 8 seconds (stop phase before next cycle)
6. **Real-time Updates** - Frontend polls backend every 5 seconds for updates
7. **Data Visualization** - Displays live graphs, statistics, and ML training status

## 🚗 Supported Vehicle Classes

- 🚗 Car
- 🏍️ Motorcycle
- 🚌 Bus
- 🚛 Truck

## 📊 Dashboard Features

### Live Camera Feed
- Real-time video stream with vehicle detection boxes
- Vehicle labels and bounding boxes
- Traffic signal status overlay
- ML training status indicator ("LEARNING" or "TRAINED")

### Traffic Statistics
- Current vehicle count
- ML model training status
- Traffic density cluster label
- Real-time updates

### Analytics Graph
- Vehicle count over time (last 20 data points)
- Interactive Chart.js visualization
- 5-second update interval

### Map View
- Interactive map showing camera location
- Powered by OpenStreetMap and Leaflet
- Marker with location details

## 🔧 Configuration

### API Architecture

The backend uses a clean REST API structure with `/api` prefix:

```
Backend API Endpoints (Flask - Port 5000):
├── /video_feed              - Video stream (MJPEG)
├── /api/traffic_status      - GET traffic light state & ML status
├── /api/train_model         - POST manually trigger ML training
├── /api/reset_model         - POST reset ML model & data
├── /api/toggle_auto_train   - POST enable/disable auto-training
└── /api/health              - GET health check

Frontend (React - Port 3000 in dev):
├── Vite dev server proxies /api and /video_feed to backend
├── React Router handles /dashboard, /map routes
└── All API calls use /api prefix to avoid routing conflicts
```

**Why `/api` prefix?**
- Prevents routing conflicts between Flask and React Router
- Clean separation of concerns (API vs frontend routes)
- Allows proper SPA routing (refresh on /dashboard works correctly)
- Industry-standard pattern for fullstack applications

### Backend Configuration (app.py)

```python
# Camera settings
cap = cv2.VideoCapture(0)  # Change 0 to camera index

# Vehicle classes (COCO dataset)
VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

# Adaptive traffic controller settings
traffic_controller = AdaptiveTrafficController(
    n_clusters=3,        # Number of traffic density clusters (low, medium, high)
    history_size=100     # Maximum historical observations to retain
)

# ML Model Training
min_samples_for_training = 30  # Minimum observations before training starts
```

### ML Controller Parameters

You can customize the unsupervised learning behavior:

```python
# In AdaptiveTrafficController class initialization
traffic_controller = AdaptiveTrafficController(
    n_clusters=3,                  # Number of traffic clusters (default: 3)
    history_size=100,              # Size of rolling history window
    min_samples_for_training=15    # Samples needed before first training (reduced for faster demos)
)

# Frame sampling for faster data collection
self.sample_interval = 15  # Sample every 15 frames (~1 sample per second at 15fps)
```

**Why min_samples=15?**
- Allows faster training for demos and testing (~30 seconds)
- Still provides enough data for meaningful clustering
- Perfect for YouTube video demos or testing scenarios
- For production, you can increase to 30-50 for more robust patterns

### Frontend Configuration (vite.config.js)

```javascript
server: {
  port: 5173,  // Default Vite port
  proxy: {
    '/video_feed': 'http://localhost:5000',
    '/traffic_status': 'http://localhost:5000'
  }
}
```

### Environment Variables

- `VIDEO_SOURCE`: Path to video file (optional, defaults to webcam)
- `PORT`: Backend server port (default: 5000)

## 🐛 Troubleshooting

### PyTorch Model Loading Issue

If you encounter `_pickle.UnpicklingError` with newer PyTorch versions, the code includes a fix:

```python
# Monkey patch torch.load to use weights_only=False
original_load = torch.load
def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_load(*args, **kwargs)
torch.load = patched_load
```

### Camera Not Working

- **Check usage**: Ensure camera isn't being used by another application
- **Permissions**: Verify camera permissions in Windows/macOS settings
- **Alternative camera**: The app automatically tries indexes 0, 1, 2
- **Use video file**: Set `VIDEO_SOURCE` environment variable to a video file path
- **Placeholder mode**: If no source is found, a placeholder with grid pattern will display

### Port Already in Use

- **Frontend**: Change port in `vite.config.js` (default: 5173)
- **Backend**: Change port in `app.py`: `app.run(port=5001)` or set `PORT` environment variable

### Performance Issues

- **High memory usage**: See [Performance & Memory Optimization](#-performance--memory-optimization) section
- **Reduce frame rate**: Modify `time.sleep(0.067)` in `process_frame()` to increase delay (e.g., 0.1 for ~10fps)
- **Lower resolution**: Adjust camera resolution in `init_camera()` (480x360 instead of 640x480)
- **Skip frames**: Process every 2nd or 3rd frame instead of every frame
- **Lower JPEG quality**: Reduce `cv2.IMWRITE_JPEG_QUALITY` parameter from 80 to 60
- **Enable GPU**: Install PyTorch with CUDA support for GPU acceleration
  ```bash
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
  ```

### Module Not Found Errors

```bash
# Ensure virtual environment is activated
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Reinstall dependencies
pip install -r requirements.txt
npm install
```

## 🚀 Building for Production

```bash
npm run build
```

The production build will be in the `dist/` folder. The Flask backend will automatically serve the built React app from the `dist/` folder.

## ⚡ Performance & Memory Optimization

### Reduce Memory Consumption

1. **Use YOLOv8 Nano Model** (already configured)
   - Smallest YOLOv8 variant (~6MB)
   - Balanced accuracy and speed

2. **Lower Video Resolution**
   ```python
   # In app.py init_camera() function
   cam.set(cv2.CAP_PROP_FRAME_WIDTH, 480)   # Reduce from 640
   cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)  # Reduce from 480
   ```

3. **Reduce Frame Rate**
   ```python
   # In process_frame() function
   time.sleep(0.1)  # Increase from 0.067 for ~10 fps instead of 15 fps
   ```

4. **Use Headless OpenCV**
   - Already using `opencv-python-headless` in requirements.txt
   - Reduces dependencies and memory footprint

5. **Limit Detection Frequency**
   ```python
   # Skip frames for detection
   frame_count = 0
   if frame_count % 3 == 0:  # Detect every 3rd frame
       vehicles = detect_vehicles(frame)
   frame_count += 1
   ```

6. **Optimize JPEG Encoding**
   ```python
   # Lower JPEG quality to reduce bandwidth
   cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])  # Reduce from 80
   ```

### Typical Memory Usage

- **Minimal setup**: ~800MB RAM (YOLOv8n + Flask + OpenCV)
- **With frontend**: ~1.2GB RAM total
- **GPU acceleration**: Requires ~2GB VRAM (optional)

## 🔮 Future Enhancements

- [ ] Multi-camera intersection support
- [ ] Emergency vehicle prioritization
- [ ] Historical data analytics and visualization
- [ ] Mobile app integration
- [ ] Wireless sensor integration (see `Wireless type/` folder)
- [ ] Advanced ML models (LSTM for time-series prediction)
- [ ] Multi-objective optimization (wait time + throughput)
- [ ] Real-time model retraining with online learning

## 📝 License

This project is for educational and research purposes.

## 👨‍💻 Author

**Manaswin Sripatnala**

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 🙏 Acknowledgments

- [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) - Object detection model
- [OpenCV](https://opencv.org/) - Computer vision library
- [React](https://react.dev/) - Frontend framework
- [Flask](https://flask.palletsprojects.com/) - Backend framework
- [Chart.js](https://www.chartjs.org/) - Data visualization
- [Leaflet](https://leafletjs.com/) - Interactive maps

---

⭐ Star this repository if you find it helpful!
