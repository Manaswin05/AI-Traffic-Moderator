from flask import Flask, render_template, Response, jsonify, send_from_directory, request
from flask_cors import CORS
import cv2
import time
import torch
import numpy as np
import os
import pickle
import threading
from sklearn.cluster import KMeans
from collections import deque

video_lock = threading.Lock()

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

# Warm up the YOLO model to prevent first-frame lag when frontend connects
print("Warming up YOLO model...")
dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
_ = model(dummy_frame, verbose=False)
print("[+] YOLO model warmed up and ready!")

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
        else:
            print(f"WARNING: Found file {video_path} but could not open it (might be a Git LFS pointer).")

    # 2. Try physical webcam only if NOT running in a cloud container (Hugging Face/Render)
    is_cloud = os.environ.get("SPACE_ID") or os.environ.get("RENDER") or os.environ.get("PORT") == "7860"
    if not is_cloud:
        for index in [0, 1, 2]:
            try:
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
            except Exception:
                pass
    else:
        print("INFO: Headless cloud environment detected. Skipping webcam detection loop.")

    print("WARNING: No camera or video file found. Will stream placeholder frames.")
    return None, False

cap, is_video_file = init_camera()

VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

# ============================================
# K-Means Traffic Classification System
# Memory-optimized for Render free tier (512MB)
# ============================================

class TrafficKMeansOptimized:
    """Memory-efficient K-means for traffic classification"""
    
    def __init__(self):
        # Memory-optimized parameters for Render free tier
        self.MIN_SAMPLES = 20              # Start with minimal data
        self.RETRAIN_INTERVAL = 150        # Less frequent retraining
        self.MAX_DATA_SIZE = 200           # Small rolling window (~1.6KB)
        
        # Use deque for memory efficiency (automatic size limit)
        self.training_data = deque(maxlen=self.MAX_DATA_SIZE)
        
        # Model state
        self.model = None
        self.cluster_centers = None
        self.samples_since_last_train = 0
        self.last_train_time = time.time()
        self.is_trained = False
        
        # Pre-seed with realistic traffic patterns for immediate operation
        # This allows K-means to work from the start without waiting
        initial_patterns = [
            1, 2, 2, 3, 3, 4, 5,           # Low traffic
            7, 8, 9, 10, 11, 12,           # Medium traffic  
            15, 17, 18, 20, 22, 25         # High traffic
        ]
        for count in initial_patterns:
            self.training_data.append(count)
        
        # Try to load existing model
        self.load_model()
        
        # If no saved model, train with seed data
        if not self.is_trained:
            self.train()
    
    def add_sample(self, vehicle_count):
        """Add new sample and intelligently decide on retraining"""
        self.training_data.append(vehicle_count)
        self.samples_since_last_train += 1
        
        # Decision logic for retraining
        should_retrain = False
        
        # Periodic retraining after enough new data
        if self.samples_since_last_train >= self.RETRAIN_INTERVAL:
            should_retrain = True
        
        # Time-based safety net (retrain every 3 hours minimum)
        elif time.time() - self.last_train_time > 10800:
            should_retrain = True
        
        if should_retrain:
            self.train()
            self.save_model()
    
    def train(self):
        """Train K-means model - memory efficient"""
        if len(self.training_data) < self.MIN_SAMPLES:
            return
        
        try:
            # Convert deque to numpy array (shape: n_samples, 1)
            X = np.array(list(self.training_data)).reshape(-1, 1)
            
            # Train K-means with 3 clusters (low, medium, high)
            self.model = KMeans(
                n_clusters=3, 
                random_state=42,
                n_init=10,           # Reduced from default for speed
                max_iter=100         # Reduced from 300 for speed
            )
            self.model.fit(X)
            
            # Sort cluster centers to ensure: 0=low, 1=medium, 2=high
            centers = self.model.cluster_centers_.flatten()
            sorted_indices = np.argsort(centers)
            
            # Create mapping: old_label -> new_label
            self.label_mapping = {old: new for new, old in enumerate(sorted_indices)}
            self.cluster_centers = np.sort(centers)
            
            self.samples_since_last_train = 0
            self.last_train_time = time.time()
            self.is_trained = True
            
            print(f"[+] K-means trained | Centers: {self.cluster_centers.round(1)}")
            
        except Exception as e:
            print(f"[-] K-means training error: {e}")
    
    def classify(self, vehicle_count):
        """Classify traffic density - returns (cluster, density_label)"""
        if not self.is_trained or self.model is None:
            # Fallback to simple rules if model not ready
            return self._fallback_classification(vehicle_count)
        
        try:
            # Predict cluster
            cluster = self.model.predict([[vehicle_count]])[0]
            
            # Remap to sorted cluster (0=low, 1=medium, 2=high)
            cluster = self.label_mapping[cluster]
            
            # Map to density label
            density_labels = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}
            density = density_labels[cluster]
            
            return cluster, density
            
        except Exception as e:
            print(f"[-] Classification error: {e}")
            return self._fallback_classification(vehicle_count)
    
    def _fallback_classification(self, vehicle_count):
        """Simple rule-based fallback when model isn't ready"""
        if vehicle_count <= 5:
            return 0, "LOW"
        elif vehicle_count <= 12:
            return 1, "MEDIUM"
        else:
            return 2, "HIGH"
    
    def save_model(self):
        """Save model to disk"""
        try:
            os.makedirs('models', exist_ok=True)
            model_data = {
                'model': self.model,
                'cluster_centers': self.cluster_centers,
                'label_mapping': self.label_mapping,
                'training_data': list(self.training_data)
            }
            with open('models/traffic_kmeans.pkl', 'wb') as f:
                pickle.dump(model_data, f)
            print("[+] Model saved successfully")
        except Exception as e:
            print(f"[-] Model save error: {e}")
    
    def load_model(self):
        """Load model from disk if exists"""
        try:
            with open('models/traffic_kmeans.pkl', 'rb') as f:
                model_data = pickle.load(f)
                self.model = model_data['model']
                self.cluster_centers = model_data['cluster_centers']
                self.label_mapping = model_data['label_mapping']
                self.is_trained = True
                print(f"[+] Model loaded | Centers: {self.cluster_centers.round(1)}")
        except FileNotFoundError:
            print("[i] No saved model found - will train from seed data")
        except Exception as e:
            print(f"[-] Model load error: {e}")
    
    def get_stats(self):
        """Get model statistics"""
        return {
            "trained": self.is_trained,
            "samples_collected": len(self.training_data),
            "cluster_centers": self.cluster_centers.tolist() if self.cluster_centers is not None else None,
            "samples_since_retrain": self.samples_since_last_train,
            "next_retrain_in": self.RETRAIN_INTERVAL - self.samples_since_last_train
        }


# Initialize K-means system
kmeans_system = TrafficKMeansOptimized()

traffic_state = {
    "signal": "red",
    "timer": 15,
    "last_change": time.time(),
    "vehicle_count": 0,
    "traffic_density": "LOW",
    "cluster": 0
}


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

    consecutive_failures = 0

    while True:
        current_cap = cap
        
        if current_cap is None:
            frame_bytes = make_placeholder_frame("No camera / video source found")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(1)
            continue

        try:
            with video_lock:
                ret, frame = current_cap.read()
        except Exception:
            ret, frame = False, None

        # Loop video file when it ends
        if not ret and is_video_file:
            try:
                with video_lock:
                    current_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = current_cap.read()
            except Exception:
                ret, frame = False, None

        if not ret or frame is None or frame.size == 0:
            consecutive_failures += 1

            if consecutive_failures >= 10:
                frame_bytes = make_placeholder_frame("Camera disconnected or loading...")
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

        # === K-MEANS TRAFFIC CLASSIFICATION ===
        # Add sample for continuous learning
        kmeans_system.add_sample(vehicle_count)
        
        # Classify current traffic density
        cluster, density = kmeans_system.classify(vehicle_count)
        
        # Update traffic state
        traffic_state["vehicle_count"] = vehicle_count
        traffic_state["traffic_density"] = density
        traffic_state["cluster"] = cluster
        
        # === AI-DRIVEN SIGNAL LOGIC ===
        current_time = time.time()
        elapsed_time = current_time - traffic_state["last_change"]

        if elapsed_time >= traffic_state["timer"]:
            if traffic_state["signal"] == "red":
                # Use AI classification instead of fixed thresholds
                if density == "HIGH":
                    traffic_state["signal"] = "green"
                    traffic_state["timer"] = 20  # Longer green for high traffic
                elif density == "MEDIUM":
                    traffic_state["signal"] = "yellow"
                    traffic_state["timer"] = 8
                else:  # LOW
                    traffic_state["signal"] = "red"
                    traffic_state["timer"] = 10  # Short red for low traffic
            elif traffic_state["signal"] == "green":
                traffic_state["signal"] = "yellow"
                traffic_state["timer"] = 4
            elif traffic_state["signal"] == "yellow":
                traffic_state["signal"] = "red"
                traffic_state["timer"] = 10

            traffic_state["last_change"] = current_time

        # Overlay text on frame with AI info
        signal_colors = {"red": (0, 0, 255), "yellow": (0, 255, 255), "green": (0, 255, 0)}
        sig_color = signal_colors.get(traffic_state["signal"], (255, 255, 255))
        
        density_colors = {"LOW": (0, 255, 0), "MEDIUM": (0, 255, 255), "HIGH": (0, 0, 255)}
        dens_color = density_colors.get(density, (255, 255, 255))
        
        cv2.putText(frame, f"Signal: {traffic_state['signal'].upper()}",
                    (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, sig_color, 2)
        cv2.putText(frame, f"Vehicles: {vehicle_count}",
                    (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        cv2.putText(frame, f"AI Density: {density}",
                    (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.8, dens_color, 2)
        cv2.putText(frame, f"Cluster: {cluster}",
                    (20, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)

        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

        # Throttle to ~15 fps to reduce CPU on cloud
        time.sleep(0.067)


# ---------------------------
# Flask Routes
# ---------------------------
@app.route('/set_video_source', methods=['POST'])
def set_video_source():
    global cap, is_video_file
    data = request.json
    source_type = data.get('source', 'video')

    with video_lock:
        if cap is not None:
            cap.release()

    if source_type == 'webcam':
        for index in [0, 1, 2]:
            temp_cap = cv2.VideoCapture(index)
            if temp_cap.isOpened():
                temp_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                temp_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                temp_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                temp_cap.set(cv2.CAP_PROP_FPS, 30)
                with video_lock:
                    cap = temp_cap
                    is_video_file = False
                return jsonify({"status": "success", "message": f"Switched to webcam {index}"})

        with video_lock:
            cap = None
            is_video_file = False
        return jsonify({"status": "error", "message": "No webcam found"}), 404

    else:
        video_path = os.environ.get("VIDEO_SOURCE", "demo_traffic.mp4")
        if os.path.exists(video_path):
            temp_cap = cv2.VideoCapture(video_path)
            with video_lock:
                cap = temp_cap
                is_video_file = True
            return jsonify({"status": "success", "message": "Switched to demo video"})

        with video_lock:
            cap = None
            is_video_file = False
        return jsonify({"status": "error", "message": "Demo video not found"}), 404

@app.route('/video_feed')
def video_feed():
    return Response(process_frame(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/traffic_status')
def traffic_status():
    stats = kmeans_system.get_stats()
    return jsonify({
        "traffic_light": traffic_state["signal"],
        "vehicle_count": traffic_state["vehicle_count"],
        "traffic_density": traffic_state["traffic_density"],
        "cluster": traffic_state["cluster"],
        "model_trained": stats["trained"],
        "samples_collected": stats["samples_collected"],
        "cluster_centers": stats["cluster_centers"]
    })


@app.route('/model_info')
def model_info():
    """Get detailed K-means model information"""
    return jsonify(kmeans_system.get_stats())


@app.route('/train_model', methods=['POST'])
def train_model():
    """Manually trigger model retraining"""
    kmeans_system.train()
    kmeans_system.save_model()
    return jsonify({
        "status": "success",
        "message": "Model retrained successfully",
        "stats": kmeans_system.get_stats()
    })


# Serve React frontend for all non-API routes (SPA support)
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
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
    print("Flask server: http://localhost:5000")
    print("=" * 50)

    try:
        app.run(debug=False, threaded=True, host='0.0.0.0', port=5000)
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        print("Shutdown complete.")
