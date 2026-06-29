---
title: AI Traffic Moderator
emoji: 🚦
colorFrom: red
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# AI Traffic Control System 🚦

A modern AI-powered traffic signal control system that uses **YOLOv8** for real-time vehicle detection and dynamically manages traffic signals. Built with **React**, **Flask**, **OpenCV**, and **Ultralytics YOLO**.

![Traffic Control System](https://img.shields.io/badge/AI-Traffic%20Control-blue)
![React](https://img.shields.io/badge/React-18.2.0-61dafb)
![Flask](https://img.shields.io/badge/Flask-3.0.0-000000)
![Python](https://img.shields.io/badge/Python-3.11-3776ab)

## ✨ Features

- 🎯 **Real-time Vehicle Detection** - YOLOv8 powered detection for cars, motorcycles, buses, and trucks
- 🚦 **Dynamic Traffic Signal Control** - AI-based signal timing based on vehicle density
- 📊 **Live Analytics Dashboard** - Real-time vehicle count graphs and statistics
- 🗺️ **Interactive Map View** - Traffic camera location visualization with Leaflet
- 📹 **Live Video Streaming** - Real-time camera feed with vehicle annotations
- 🎨 **Modern UI** - Professional React-based interface with smooth animations
- 📱 **Responsive Design** - Works seamlessly on desktop and mobile devices

## 🛠️ Tech Stack

### Frontend
- **React 18** - Modern UI framework
- **React Router** - Client-side routing
- **Chart.js** - Real-time data visualization
- **React Leaflet** - Interactive maps
- **Axios** - HTTP client
- **Vite** - Fast build tool

### Backend
- **Flask** - Python web framework
- **OpenCV** - Video processing
- **YOLOv8 (Ultralytics)** - Object detection
- **PyTorch** - Deep learning framework

## 📋 Prerequisites

- **Python 3.8+**
- **Node.js 16+** and npm
- **Webcam** (for live detection)
- **Git**

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/AI-Traffic-Moderator.git
cd AI-Traffic-Moderator
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Node.js Dependencies

```bash
npm install
```

## 🎮 Running the Application

You need to run both the backend and frontend servers:

### Terminal 1: Start Flask Backend

```bash
python app.py
```

The backend will run on `http://localhost:5000`

### Terminal 2: Start React Frontend

```bash
npm run dev
```

The frontend will run on `http://localhost:3000`

### Access the Application

Open your browser and navigate to:
```
http://localhost:3000
```

**Login:** Use any username and password (demo authentication)

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
├── app.py                       # Flask backend server
├── requirements.txt             # Python dependencies
├── package.json                 # Node.js dependencies
├── vite.config.js              # Vite configuration
└── README.md                    # This file
```

## 🎯 How It Works

1. **Video Capture** - Captures live video feed from webcam
2. **Vehicle Detection** - YOLOv8 processes each frame to detect vehicles
3. **Traffic Analysis** - Counts vehicles and determines traffic density
4. **Signal Control** - Adjusts traffic signal timing dynamically:
   - **Red**: Low traffic (< 5 vehicles) - 15 seconds
   - **Yellow**: Medium traffic (5-9 vehicles) - 10 seconds
   - **Green**: High traffic (≥ 10 vehicles) - 15 seconds
5. **Real-time Updates** - Frontend polls backend every 5 seconds for updates
6. **Data Visualization** - Displays live graphs and statistics

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

### Traffic Statistics
- Current vehicle count
- System status indicator
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

### Backend Configuration (app.py)

```python
# Camera settings
cap = cv2.VideoCapture(0)  # Change 0 to camera index

# Vehicle classes (COCO dataset)
VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

# Traffic signal timing
traffic_state = {
    "signal": "red",
    "timer": 15,
    "vehicle_count": 0
}
```

### Frontend Configuration (vite.config.js)

```javascript
server: {
  port: 3000,
  proxy: {
    '/video_feed': 'http://localhost:5000',
    '/traffic_status': 'http://localhost:5000'
  }
}
```

## 🐛 Troubleshooting

### PyTorch 2.6 Model Loading Issue

If you encounter `_pickle.UnpicklingError`, the code includes a fix:

```python
# Monkey patch torch.load to use weights_only=False
original_load = torch.load
def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_load(*args, **kwargs)
torch.load = patched_load
```

### Camera Not Working

- Check if camera is being used by another application
- Verify camera permissions in Windows settings
- Try changing camera index in `app.py`: `cv2.VideoCapture(1)` or `cv2.VideoCapture(2)`

### Port Already in Use

- Frontend: Change port in `vite.config.js`
- Backend: Change port in `app.py`: `app.run(port=5001)`

## 🚀 Building for Production

```bash
npm run build
```

The production build will be in the `dist/` folder.

## 🔮 Future Enhancements

- [ ] Multi-camera intersection support
- [ ] Emergency vehicle prioritization
- [ ] Cloud-based deployment
- [ ] Historical data analytics
- [ ] Mobile app integration
- [ ] Wireless sensor integration (see `Wireless type/` folder)

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
