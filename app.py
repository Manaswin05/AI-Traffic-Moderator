from flask import Flask, render_template, Response, jsonify, send_from_directory
from flask_cors import CORS
import cv2
import time
import torch
import numpy as np
import os
import pickle
import gc
from sklearn.cluster import KMeans
from collections import deque

# ============================================
# MEMORY OPTIMIZATION FOR 512MB RAM
# ============================================

# Force CPU-only mode to save GPU memory
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

# Limit OpenMP threads for CPU inference
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

# PyTorch memory optimization
torch.set_num_threads(1)
torch.set_num_interop_threads(1)

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

# Load YOLO model with aggressive memory optimization
print("Loading YOLO model (optimized for 512MB RAM)...")
model = YOLO("models/yolov8n.pt")
model.overrides['verbose'] = False  # Disable verbose output
model.overrides['imgsz'] = 320      # Smaller input size (default 640)
model.overrides['half'] = False     # Don't use FP16 on CPU
model.overrides['device'] = 'cpu'   # Force CPU
print(f"✓ YOLO loaded | Input size: 320x320 | Device: CPU")

# ---------------------------
# Camera / Video Initialization
# ---------------------------
class SyntheticVideoGenerator:
    """Generate synthetic traffic video for cloud deployment without video files"""
    
    def __init__(self, width=480, height=360):
        self.width = width
        self.height = height
        self.frame_count = 0
        self.vehicle_positions = []
        self.max_vehicles = 25
        
        # Initialize some random vehicles
        for _ in range(5):
            self.vehicle_positions.append({
                'x': np.random.randint(50, width - 100),
                'y': np.random.randint(50, height - 100),
                'vx': np.random.randint(-2, 3),
                'vy': np.random.randint(-2, 3),
                'type': np.random.choice([2, 3, 5, 7])  # car, motorcycle, bus, truck
            })
        
        print("SUCCESS: Using synthetic video generator (cloud mode)")
    
    def read(self):
        """Generate a frame with moving vehicles"""
        # Create base frame (road-like background)
        frame = np.ones((self.height, self.width, 3), dtype=np.uint8) * 40  # Dark gray
        
        # Draw road lines
        for i in range(0, self.width, 60):
            cv2.line(frame, (i, 0), (i, self.height), (80, 80, 80), 2)
        for i in range(0, self.height, 60):
            cv2.line(frame, (0, i), (self.width, i), (80, 80, 80), 2)
        
        # Draw center dividing line
        for i in range(0, self.height, 40):
            cv2.rectangle(frame, (self.width//2 - 5, i), (self.width//2 + 5, i + 20), (200, 200, 200), -1)
        
        # Update and draw vehicles
        for vehicle in self.vehicle_positions:
            # Update position
            vehicle['x'] += vehicle['vx']
            vehicle['y'] += vehicle['vy']
            
            # Bounce off edges
            if vehicle['x'] < 20 or vehicle['x'] > self.width - 60:
                vehicle['vx'] *= -1
            if vehicle['y'] < 20 or vehicle['y'] > self.height - 60:
                vehicle['vy'] *= -1
            
            # Draw vehicle as a colored rectangle
            color_map = {2: (0, 255, 0), 3: (255, 255, 0), 5: (0, 0, 255), 7: (255, 0, 0)}
            color = color_map.get(vehicle['type'], (255, 255, 255))
            
            x, y = int(vehicle['x']), int(vehicle['y'])
            size = 40 if vehicle['type'] in [5, 7] else 30  # Larger for bus/truck
            cv2.rectangle(frame, (x, y), (x + size, y + size), color, -1)
            cv2.rectangle(frame, (x, y), (x + size, y + size), (255, 255, 255), 2)
        
        # Randomly add or remove vehicles
        self.frame_count += 1
        if self.frame_count % 60 == 0:  # Every 60 frames
            if len(self.vehicle_positions) < self.max_vehicles and np.random.random() > 0.5:
                # Add new vehicle
                self.vehicle_positions.append({
                    'x': np.random.randint(50, self.width - 100),
                    'y': np.random.randint(50, self.height - 100),
                    'vx': np.random.randint(-2, 3),
                    'vy': np.random.randint(-2, 3),
                    'type': np.random.choice([2, 3, 5, 7])
                })
            elif len(self.vehicle_positions) > 2 and np.random.random() > 0.7:
                # Remove a vehicle
                self.vehicle_positions.pop(np.random.randint(0, len(self.vehicle_positions)))
        
        return True, frame
    
    def isOpened(self):
        return True
    
    def release(self):
        pass
    
    def set(self, prop, value):
        pass


def init_camera():
    # 1. Try physical webcam (works locally)
    for index in [0, 1, 2]:
        try:
            cam = cv2.VideoCapture(index)
            if cam.isOpened():
                cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cam.set(cv2.CAP_PROP_FRAME_WIDTH, 480)   # Lower resolution
                cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
                cam.set(cv2.CAP_PROP_FPS, 15)            # Lower FPS

                for _ in range(5):
                    cam.read()

                ret, frame = cam.read()
                if ret and frame is not None and frame.size > 0:
                    print(f"SUCCESS: Camera {index} opened. Shape: {frame.shape}")
                    return cam, False  # (capture, is_video_file)
                else:
                    cam.release()
        except Exception as e:
            print(f"Camera {index} failed: {e}")
            continue

    # 2. Fallback to synthetic video generator (cloud/headless mode)
    print("INFO: No physical camera found. Using synthetic video generator (cloud mode).")
    return SyntheticVideoGenerator(), False

cap, is_video_file = init_camera()

VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

# ============================================
# K-Means Traffic Classification System
# Memory-optimized for Render free tier (512MB)
# ============================================

class TrafficKMeansOptimized:
    """Memory-efficient K-means for traffic classification - Optimized for 512MB RAM"""
    
    def __init__(self):
        # Ultra-aggressive memory optimization for Render free tier
        self.MIN_SAMPLES = 15              # Minimal data to start
        self.RETRAIN_INTERVAL = 200        # Less frequent retraining
        self.MAX_DATA_SIZE = 100           # Smaller rolling window (~800 bytes)
        
        # Use deque for memory efficiency (automatic size limit)
        self.training_data = deque(maxlen=self.MAX_DATA_SIZE)
        
        # Model state
        self.model = None
        self.cluster_centers = None
        self.samples_since_last_train = 0
        self.last_train_time = time.time()
        self.is_trained = False
        
        # Pre-seed with realistic traffic patterns for immediate operation
        initial_patterns = [1, 2, 3, 4, 5, 8, 10, 12, 15, 18, 20, 25]
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
            X = np.array(list(self.training_data), dtype=np.float32).reshape(-1, 1)
            
            # Train K-means with 3 clusters (low, medium, high)
            self.model = KMeans(
                n_clusters=3, 
                random_state=42,
                n_init=5,            # Reduced from 10 for speed/memory
                max_iter=50          # Reduced from 100 for speed/memory
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
            
            print(f"✓ K-means trained | Centers: {self.cluster_centers.round(1)}")
            
            # Force garbage collection after training
            gc.collect()
            
        except Exception as e:
            print(f"✗ K-means training error: {e}")
    
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
            print(f"✗ Classification error: {e}")
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
            print("✓ Model saved successfully")
        except Exception as e:
            print(f"✗ Model save error: {e}")
    
    def load_model(self):
        """Load model from disk if exists"""
        try:
            with open('models/traffic_kmeans.pkl', 'rb') as f:
                model_data = pickle.load(f)
                self.model = model_data['model']
                self.cluster_centers = model_data['cluster_centers']
                self.label_mapping = model_data['label_mapping']
                self.is_trained = True
                print(f"✓ Model loaded | Centers: {self.cluster_centers.round(1)}")
        except FileNotFoundError:
            print("○ No saved model found - will train from seed data")
        except Exception as e:
            print(f"✗ Model load error: {e}")
    
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
# Vehicle Detection Function (Memory Optimized)
# ---------------------------
def detect_vehicles(frame):
    # Resize frame for faster inference and lower memory usage
    h, w = frame.shape[:2]
    if w > 480:
        scale = 480 / w
        frame = cv2.resize(frame, (480, int(h * scale)))
    
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Run inference with memory optimization
    results = model(rgb_frame, verbose=False, imgsz=320)[0]
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
    # Smaller frame size to save memory
    frame = np.zeros((360, 480, 3), dtype=np.uint8)
    # Dark background with grid lines for visual interest
    for i in range(0, 480, 40):
        cv2.line(frame, (i, 0), (i, 360), (20, 20, 20), 1)
    for i in range(0, 360, 40):
        cv2.line(frame, (0, i), (480, i), (20, 20, 20), 1)
    cv2.putText(frame, message, (60, 165),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 180, 255), 2)
    cv2.putText(frame, "AI Traffic Control System", (70, 200),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
    return buffer.tobytes()


# ---------------------------
# Video Processing Generator (Memory Optimized)
# ---------------------------
frame_counter = 0  # Global counter for frame skipping

def process_frame():
    global cap, is_video_file, frame_counter

    # Always have a valid source (synthetic or real camera)
    if cap is None:
        print("ERROR: No video source initialized")
        while True:
            frame_bytes = make_placeholder_frame("Initializing video source...")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(1)
        return

    print("Starting video feed stream...")
    consecutive_failures = 0

    while True:
        try:
            ret, frame = cap.read()

            if not ret or frame is None or frame.size == 0:
                consecutive_failures += 1
                print(f"Frame read failed (attempt {consecutive_failures}/10)")

                if consecutive_failures >= 10:
                    frame_bytes = make_placeholder_frame("Video source error")
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                    time.sleep(1)
                    consecutive_failures = 0
                else:
                    time.sleep(0.05)
                continue

            consecutive_failures = 0
            frame_counter += 1
            
            # Process every 2nd frame to reduce CPU/memory load (skip frames)
            if frame_counter % 2 != 0:
                time.sleep(0.033)  # ~30fps timing
                continue

            vehicles = detect_vehicles(frame)
            vehicle_count = len(vehicles)

            # Draw bounding boxes (only for detected vehicles to save processing)
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
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, sig_color, 2)
            cv2.putText(frame, f"Vehicles: {vehicle_count}",
                        (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(frame, f"Density: {density}",
                        (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, dens_color, 2)

            # Lower JPEG quality to reduce bandwidth and memory
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            frame_bytes = buffer.tobytes()
            
            # Clear buffer to free memory
            del buffer
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # Periodic garbage collection every 50 frames
            if frame_counter % 50 == 0:
                gc.collect()

            # Throttle to ~10 fps to reduce CPU/memory on cloud (skip every other frame)
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error in video processing: {e}")
            frame_bytes = make_placeholder_frame(f"Error: {str(e)}")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(1)


# ---------------------------
# Flask Routes
# ---------------------------
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
    print("Memory Optimized for 512MB RAM")
    print("=" * 50)
    
    video_source = "Synthetic Video (Cloud Mode)" if isinstance(cap, SyntheticVideoGenerator) else "Physical Camera"
    print(f"Video Source: {video_source}")
    print(f"YOLO Mode: CPU-only (320x320)")
    print(f"Resolution: 480x360")
    print(f"Frame Rate: ~10 fps")
    print("Flask server: Starting...")
    print("=" * 50)

    try:
        app.run(debug=False, threaded=True, host='0.0.0.0', port=5000)
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        print("Shutdown complete.")
