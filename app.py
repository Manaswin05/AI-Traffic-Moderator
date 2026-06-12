from flask import Flask, render_template, Response, jsonify, send_from_directory, request
from flask_cors import CORS
import cv2
import time
import torch
import numpy as np
import os
from sklearn.cluster import KMeans
from collections import deque

# Monkey patch torch.load to use weights_only=False
original_load = torch.load
def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_load(*args, **kwargs)
torch.load = patched_load

from ultralytics import YOLO

# Serve React build in production
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'dist')
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='')
CORS(app)

model = YOLO("models/yolov8n.pt")

# ---------------------------
# Camera / Video Initialization
# ---------------------------
def init_camera():
    # 1. Try a demo video file first (good for cloud/Render deployment)
    video_path = os.environ.get("VIDEO_SOURCE", "demo_traffic.mp4")
    if os.path.exists(video_path):
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            print(f"SUCCESS: Using video file: {video_path}")
            return cap, True  # (capture, is_video_file)

    # 2. Try physical webcam (works locally)
    for index in [0, 1, 2]:
        cam = cv2.VideoCapture(index)
        if cam.isOpened():
            cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cam.set(cv2.CAP_PROP_FPS, 30)

            for _ in range(5):
                cam.read()

            ret, frame = cam.read()
            if ret and frame is not None and frame.size > 0:
                print(f"SUCCESS: Camera {index} opened. Shape: {frame.shape}")
                return cam, False  # (capture, is_video_file)
            else:
                cam.release()

    print("WARNING: No camera or video file found. Will stream placeholder frames.")
    return None, False

cap, is_video_file = init_camera()

VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

traffic_state = {
    "signal": "red",
    "timer": 15,
    "last_change": time.time(),
    "vehicle_count": 0,
    "cluster_label": 0
}

# ---------------------------
# Unsupervised ML Traffic Controller
# ---------------------------
class AdaptiveTrafficController:
    """
    Uses K-Means clustering to adaptively determine traffic light timing
    based on historical vehicle count patterns.
    """
    def __init__(self, n_clusters=3, history_size=100, min_samples_for_training=15):
        self.n_clusters = n_clusters
        self.history_size = history_size
        self.vehicle_history = deque(maxlen=history_size)
        self.kmeans = None
        self.is_trained = False
        self.min_samples_for_training = min_samples_for_training  # Reduced for faster demo training
        self.frame_count = 0
        self.sample_interval = 15  # Sample every 15 frames for faster data collection
        self.auto_train_enabled = True  # Allow toggling auto-training
        
        # Signal mappings (will be learned)
        self.cluster_to_signal = {}
        self.cluster_to_timer = {}
        
    def add_observation(self, vehicle_count):
        """Add vehicle count observation to history (with sampling to speed up collection)"""
        self.frame_count += 1
        
        # Sample every Nth frame to collect data faster
        if self.frame_count % self.sample_interval == 0:
            self.vehicle_history.append(vehicle_count)
            
            # Train model automatically when we have enough data (if auto-train is enabled)
            if self.auto_train_enabled and len(self.vehicle_history) >= self.min_samples_for_training and not self.is_trained:
                self.train_model()
    
    def train_model(self):
        """Train K-Means clustering on historical vehicle data"""
        if len(self.vehicle_history) < self.min_samples_for_training:
            return
        
        # Prepare data for clustering (vehicle_count as feature)
        X = np.array(list(self.vehicle_history)).reshape(-1, 1)
        
        # Train K-Means
        self.kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        self.kmeans.fit(X)
        
        # Sort cluster centers to get low, medium, high traffic
        cluster_centers = self.kmeans.cluster_centers_.flatten()
        sorted_indices = np.argsort(cluster_centers)
        
        # Map clusters to traffic signals based on traffic density
        # Low traffic -> Short green (vehicles can pass quickly)
        # Medium traffic -> Medium green
        # High traffic -> Long green (need more time to clear)
        for idx, cluster_id in enumerate(sorted_indices):
            if idx == 0:  # Low traffic cluster
                self.cluster_to_signal[cluster_id] = "green"
                self.cluster_to_timer[cluster_id] = 15
            elif idx == 1:  # Medium traffic cluster
                self.cluster_to_signal[cluster_id] = "green"
                self.cluster_to_timer[cluster_id] = 20
            else:  # High traffic cluster
                self.cluster_to_signal[cluster_id] = "green"
                self.cluster_to_timer[cluster_id] = 30
        
        self.is_trained = True
        print(f"✓ K-Means model trained with {len(self.vehicle_history)} samples")
        print(f"  Cluster centers (vehicle counts): {sorted(cluster_centers)}")
    
    def predict_signal(self, vehicle_count):
        """
        Predict optimal traffic signal based on current vehicle count
        Returns: (signal_color, timer_duration, cluster_label)
        """
        if not self.is_trained:
            # Fallback to simple rules until model is trained
            if vehicle_count >= 10:
                return "green", 25, -1
            elif vehicle_count >= 5:
                return "green", 20, -1
            else:
                return "green", 15, -1
        
        # Predict cluster
        X = np.array([[vehicle_count]])
        cluster_label = self.kmeans.predict(X)[0]
        
        signal = self.cluster_to_signal.get(cluster_label, "green")
        timer = self.cluster_to_timer.get(cluster_label, 20)
        
        return signal, timer, int(cluster_label)
    
    def retrain_periodically(self):
        """Retrain model to adapt to changing traffic patterns"""
        if len(self.vehicle_history) >= self.history_size:
            self.train_model()

# Initialize adaptive traffic controller
# Using lower min_samples (15) for faster demo training with YouTube videos
traffic_controller = AdaptiveTrafficController(n_clusters=3, history_size=100, min_samples_for_training=15)


# ---------------------------
# Vehicle Detection Function
# ---------------------------
def detect_vehicles(frame):
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = model(rgb_frame)[0]
    vehicles = []

    for box in results.boxes:
        class_id = int(box.cls[0])
        if class_id in VEHICLE_CLASSES:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            vehicles.append((class_id, (x1, y1, x2, y2)))

    return vehicles


# ---------------------------
# Error / Placeholder Frame
# ---------------------------
def make_placeholder_frame(message="No camera available"):
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Dark background with grid lines for visual interest
    for i in range(0, 640, 40):
        cv2.line(frame, (i, 0), (i, 480), (20, 20, 20), 1)
    for i in range(0, 480, 40):
        cv2.line(frame, (0, i), (640, i), (20, 20, 20), 1)
    cv2.putText(frame, message, (80, 220),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 180, 255), 2)
    cv2.putText(frame, "AI Traffic Control System", (100, 270),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)
    _, buffer = cv2.imencode('.jpg', frame)
    return buffer.tobytes()


# ---------------------------
# Video Processing Generator
# ---------------------------
def process_frame():
    global cap, is_video_file

    if cap is None:
        while True:
            frame_bytes = make_placeholder_frame("No camera / video source found")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(1)
        return

    consecutive_failures = 0

    while True:
        ret, frame = cap.read()

        # Loop video file when it ends
        if not ret and is_video_file:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()

        if not ret or frame is None or frame.size == 0:
            consecutive_failures += 1

            if consecutive_failures >= 10:
                frame_bytes = make_placeholder_frame("Camera disconnected")
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                time.sleep(1)
                consecutive_failures = 0
            else:
                time.sleep(0.05)
            continue

        consecutive_failures = 0

        vehicles = detect_vehicles(frame)
        vehicle_count = len(vehicles)

        for class_id, bbox in vehicles:
            x1, y1, x2, y2 = bbox
            label = VEHICLE_CLASSES[class_id]
            color = (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        # Add observation to adaptive controller
        traffic_controller.add_observation(vehicle_count)

        # Adaptive traffic light logic using K-Means clustering
        current_time = time.time()
        elapsed_time = current_time - traffic_state["last_change"]

        if elapsed_time >= traffic_state["timer"]:
            # Get ML-based prediction for green light duration
            predicted_signal, predicted_timer, cluster_label = traffic_controller.predict_signal(vehicle_count)
            
            # Proper traffic light state machine
            if traffic_state["signal"] == "red":
                # Red -> Green (allow traffic to flow)
                traffic_state["signal"] = "green"
                traffic_state["timer"] = predicted_timer
            elif traffic_state["signal"] == "green":
                # Green -> Yellow (prepare to stop)
                traffic_state["signal"] = "yellow"
                traffic_state["timer"] = 4
            elif traffic_state["signal"] == "yellow":
                # Yellow -> Red (stop and wait for next cycle)
                traffic_state["signal"] = "red"
                traffic_state["timer"] = 8  # Red light duration before next green
            
            traffic_state["cluster_label"] = cluster_label
            traffic_state["last_change"] = current_time

        traffic_state["vehicle_count"] = vehicle_count

        # Overlay text on frame
        signal_colors = {"red": (0, 0, 255), "yellow": (0, 255, 255), "green": (0, 255, 0)}
        sig_color = signal_colors.get(traffic_state["signal"], (255, 255, 255))
        cv2.putText(frame, f"Signal: {traffic_state['signal'].upper()}",
                    (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, sig_color, 2)
        cv2.putText(frame, f"Vehicles: {vehicle_count}",
                    (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        
        # Show ML status
        samples_collected = len(traffic_controller.vehicle_history)
        if traffic_controller.is_trained:
            ml_status = f"ML: TRAINED ({samples_collected} samples)"
        else:
            ml_status = f"ML: LEARNING ({samples_collected}/{traffic_controller.min_samples_for_training})"
        cv2.putText(frame, ml_status, (20, 130), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 200, 0), 2)

        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

        # Throttle to ~15 fps to reduce CPU on cloud
        time.sleep(0.067)


# ---------------------------
# Flask Routes
# ---------------------------
@app.route('/video_feed')
def video_feed():
    return Response(process_frame(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/traffic_status')
def traffic_status():
    return jsonify({
        "traffic_light": traffic_state["signal"],
        "vehicle_count": traffic_state["vehicle_count"],
        "ml_trained": traffic_controller.is_trained,
        "cluster_label": traffic_state.get("cluster_label", -1),
        "samples_collected": len(traffic_controller.vehicle_history),
        "min_samples_required": traffic_controller.min_samples_for_training
    })


@app.route('/api/train_model', methods=['POST'])
def train_model():
    """Manually trigger model training"""
    try:
        if len(traffic_controller.vehicle_history) < 5:
            return jsonify({
                "success": False,
                "message": f"Need at least 5 observations. Currently have {len(traffic_controller.vehicle_history)}."
            }), 400
        
        traffic_controller.train_model()
        return jsonify({
            "success": True,
            "message": f"Model trained successfully with {len(traffic_controller.vehicle_history)} samples!",
            "is_trained": traffic_controller.is_trained
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Training failed: {str(e)}"
        }), 500


@app.route('/api/reset_model', methods=['POST'])
def reset_model():
    """Reset the ML model and start fresh"""
    try:
        traffic_controller.vehicle_history.clear()
        traffic_controller.kmeans = None
        traffic_controller.is_trained = False
        traffic_controller.cluster_to_signal = {}
        traffic_controller.cluster_to_timer = {}
        traffic_controller.frame_count = 0
        
        return jsonify({
            "success": True,
            "message": "Model reset successfully. Starting fresh data collection."
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Reset failed: {str(e)}"
        }), 500


@app.route('/api/toggle_auto_train', methods=['POST'])
def toggle_auto_train():
    """Toggle automatic training on/off"""
    try:
        import json
        data = json.loads(request.data) if request.data else {}
        traffic_controller.auto_train_enabled = data.get('enabled', not traffic_controller.auto_train_enabled)
        
        return jsonify({
            "success": True,
            "auto_train_enabled": traffic_controller.auto_train_enabled,
            "message": f"Auto-training {'enabled' if traffic_controller.auto_train_enabled else 'disabled'}"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Toggle failed: {str(e)}"
        }), 500


@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "camera_active": cap is not None,
        "ml_status": "trained" if traffic_controller.is_trained else "learning"
    })


# Serve React frontend for all non-API routes (SPA support)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    # API routes should not reach here
    if path.startswith('api/') or path.startswith('video_feed'):
        return jsonify({"error": "Not found"}), 404
    
    # If running in development (no dist folder), return error message
    if not app.static_folder or not os.path.exists(app.static_folder):
        return jsonify({
            "message": "Development mode - Frontend should be served by Vite on port 3000",
            "frontend_url": "http://localhost:3000"
        })
    
    # If the path is a static file that exists, serve it
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    # Otherwise serve index.html (React Router handles the rest)
    return send_from_directory(app.static_folder, 'index.html')


# ---------------------------
# Run App
# ---------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("AI Traffic Control System - Starting")
    print("=" * 50)
    print(f"Camera/Video status: {'Ready' if cap is not None else 'NOT FOUND (placeholder mode)'}")
    print("ML Controller: K-Means Clustering (Unsupervised)")
    print("Flask server: http://localhost:5000")
    print("=" * 50)

    try:
        app.run(debug=False, threaded=True, host='0.0.0.0', port=5000)
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        print("Shutdown complete.")
