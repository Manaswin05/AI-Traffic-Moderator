from flask import Flask, render_template, Response, jsonify, send_from_directory
from flask_cors import CORS
import cv2
import time
import numpy as np
import os
import pickle
import gc
import onnxruntime as ort
from sklearn.cluster import KMeans
from collections import deque

# ============================================
# MEMORY OPTIMIZATION FOR 512MB RAM
# Using ONNX Runtime instead of PyTorch
# ONNX Runtime CPU: ~50MB vs PyTorch CPU: ~800MB
# ============================================

# Limit threads for CPU inference
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

# ============================================
# ONNX Model Loader
# ============================================

ONNX_MODEL_PATH = "models/yolov8n.onnx"
INPUT_SIZE = 320  # YOLOv8n exported at 320x320

def load_onnx_model(model_path):
    """Load YOLOv8 ONNX model with CPU-only session options."""
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 1
    opts.inter_op_num_threads = 1
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = ort.InferenceSession(
        model_path,
        sess_options=opts,
        providers=["CPUExecutionProvider"]
    )
    print(f"✓ ONNX model loaded | Input size: {INPUT_SIZE}x{INPUT_SIZE} | Provider: CPU")
    return session

print("Loading ONNX model (optimized for 512MB RAM)...")
onnx_session = load_onnx_model(ONNX_MODEL_PATH)
input_name = onnx_session.get_inputs()[0].name

# Serve React build in production
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'dist')
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='')
CORS(app)

# COCO class IDs for vehicles
VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

# ---------------------------
# Camera / Video Initialization
# ---------------------------
class SyntheticVideoGenerator:
    """Generate synthetic traffic video for cloud deployment without video files."""

    def __init__(self, width=480, height=360):
        self.width = width
        self.height = height
        self.frame_count = 0
        self.vehicle_positions = []
        self.max_vehicles = 25

        for _ in range(5):
            self.vehicle_positions.append({
                'x': np.random.randint(50, width - 100),
                'y': np.random.randint(50, height - 100),
                'vx': np.random.randint(-2, 3),
                'vy': np.random.randint(-2, 3),
                'type': np.random.choice([2, 3, 5, 7])
            })

        print("SUCCESS: Using synthetic video generator (cloud mode)")

    def read(self):
        """Generate a frame with moving vehicles."""
        frame = np.ones((self.height, self.width, 3), dtype=np.uint8) * 40

        for i in range(0, self.width, 60):
            cv2.line(frame, (i, 0), (i, self.height), (80, 80, 80), 2)
        for i in range(0, self.height, 60):
            cv2.line(frame, (0, i), (self.width, i), (80, 80, 80), 2)

        for i in range(0, self.height, 40):
            cv2.rectangle(frame, (self.width // 2 - 5, i),
                          (self.width // 2 + 5, i + 20), (200, 200, 200), -1)

        for vehicle in self.vehicle_positions:
            vehicle['x'] += vehicle['vx']
            vehicle['y'] += vehicle['vy']

            if vehicle['x'] < 20 or vehicle['x'] > self.width - 60:
                vehicle['vx'] *= -1
            if vehicle['y'] < 20 or vehicle['y'] > self.height - 60:
                vehicle['vy'] *= -1

            color_map = {2: (0, 255, 0), 3: (255, 255, 0), 5: (0, 0, 255), 7: (255, 0, 0)}
            color = color_map.get(vehicle['type'], (255, 255, 255))
            x, y = int(vehicle['x']), int(vehicle['y'])
            size = 40 if vehicle['type'] in [5, 7] else 30
            cv2.rectangle(frame, (x, y), (x + size, y + size), color, -1)
            cv2.rectangle(frame, (x, y), (x + size, y + size), (255, 255, 255), 2)

        self.frame_count += 1
        if self.frame_count % 60 == 0:
            if len(self.vehicle_positions) < self.max_vehicles and np.random.random() > 0.5:
                self.vehicle_positions.append({
                    'x': np.random.randint(50, self.width - 100),
                    'y': np.random.randint(50, self.height - 100),
                    'vx': np.random.randint(-2, 3),
                    'vy': np.random.randint(-2, 3),
                    'type': np.random.choice([2, 3, 5, 7])
                })
            elif len(self.vehicle_positions) > 2 and np.random.random() > 0.7:
                self.vehicle_positions.pop(np.random.randint(0, len(self.vehicle_positions)))

        return True, frame

    def isOpened(self):
        return True

    def release(self):
        pass

    def set(self, prop, value):
        pass


def init_camera():
    """Try physical webcam first, fall back to synthetic generator."""
    for index in [0, 1, 2]:
        try:
            cam = cv2.VideoCapture(index)
            if cam.isOpened():
                cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cam.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
                cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
                cam.set(cv2.CAP_PROP_FPS, 15)

                for _ in range(5):
                    cam.read()

                ret, frame = cam.read()
                if ret and frame is not None and frame.size > 0:
                    print(f"SUCCESS: Camera {index} opened. Shape: {frame.shape}")
                    return cam, False
                else:
                    cam.release()
        except Exception as e:
            print(f"Camera {index} failed: {e}")
            continue

    print("INFO: No physical camera found. Using synthetic video generator (cloud mode).")
    return SyntheticVideoGenerator(), False


cap, is_video_file = init_camera()

# ============================================
# ONNX Inference Helper
# ============================================

def preprocess_frame(frame):
    """Resize and normalize frame for YOLOv8 ONNX input."""
    img = cv2.resize(frame, (INPUT_SIZE, INPUT_SIZE))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32) / 255.0          # normalize to [0, 1]
    img = np.transpose(img, (2, 0, 1))            # HWC → CHW
    img = np.expand_dims(img, axis=0)             # add batch dim → (1, 3, 320, 320)
    return img


def detect_vehicles(frame):
    """
    Run ONNX inference on a single frame.
    Returns list of (class_id, (x1, y1, x2, y2)) for detected vehicles.

    YOLOv8 ONNX output shape: (1, 84, num_boxes)
      - rows 0-3 : cx, cy, w, h  in INPUT_SIZE pixel space (0–320)
      - rows 4-83: class confidence scores (no separate objectness)
    """
    h_orig, w_orig = frame.shape[:2]

    # Resize for faster inference
    if w_orig > 480:
        scale = 480 / w_orig
        frame = cv2.resize(frame, (480, int(h_orig * scale)))
        h_orig, w_orig = frame.shape[:2]

    inp = preprocess_frame(frame)
    outputs = onnx_session.run(None, {input_name: inp})

    # outputs[0]: shape (1, 84, num_boxes)
    predictions = outputs[0][0]   # → (84, num_boxes)
    predictions = predictions.T   # → (num_boxes, 84)

    vehicles = []
    conf_threshold = 0.30         # slightly lower for better recall

    # Scale from model input space (320×320) back to original frame size
    x_scale = w_orig / INPUT_SIZE
    y_scale = h_orig / INPUT_SIZE

    for pred in predictions:
        # cx, cy, w, h are in INPUT_SIZE pixel units (e.g. 0–320)
        cx, cy, bw, bh = pred[0], pred[1], pred[2], pred[3]
        class_scores = pred[4:]          # 80 COCO class scores
        class_id = int(np.argmax(class_scores))
        confidence = float(class_scores[class_id])

        if confidence < conf_threshold:
            continue
        if class_id not in VEHICLE_CLASSES:
            continue

        # Convert center+size → corners, then scale to original frame
        x1 = int((cx - bw / 2) * x_scale)
        y1 = int((cy - bh / 2) * y_scale)
        x2 = int((cx + bw / 2) * x_scale)
        y2 = int((cy + bh / 2) * y_scale)

        # Clamp to frame bounds
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w_orig, x2), min(h_orig, y2)

        # Skip degenerate boxes
        if x2 <= x1 or y2 <= y1:
            continue

        vehicles.append((class_id, (x1, y1, x2, y2)))

    return vehicles


def detect_vehicles_synthetic(cap_source):
    """
    For synthetic video (no real camera): return vehicle positions directly
    from the generator instead of running ONNX inference.
    ONNX/YOLO is trained on real photos and cannot detect drawn rectangles.
    Returns list of (class_id, (x1, y1, x2, y2)).
    """
    vehicles = []
    for v in cap_source.vehicle_positions:
        x, y = int(v['x']), int(v['y'])
        size = 40 if v['type'] in [5, 7] else 30
        vehicles.append((v['type'], (x, y, x + size, y + size)))
    return vehicles


# ============================================
# K-Means Traffic Classification System
# Memory-optimized for Render free tier (512MB)
# ============================================

class TrafficKMeansOptimized:
    """
    Adaptive K-means classifier for real-time traffic density.

    Continuously learns from live vehicle counts and classifies
    traffic into LOW / MEDIUM / HIGH clusters. Persists the trained
    model to disk so state survives service restarts.
    """

    def __init__(self):
        self.MIN_SAMPLES = 15
        self.RETRAIN_INTERVAL = 200
        self.MAX_DATA_SIZE = 100

        self.training_data = deque(maxlen=self.MAX_DATA_SIZE)
        self.model = None
        self.cluster_centers = None
        self.samples_since_last_train = 0
        self.last_train_time = time.time()
        self.is_trained = False
        self.label_mapping = {}

        # Pre-seed with realistic traffic spread
        for count in [1, 2, 3, 4, 5, 8, 10, 12, 15, 18, 20, 25]:
            self.training_data.append(count)

        self.load_model()

        if not self.is_trained:
            self.train()

    def add_sample(self, vehicle_count):
        """Add a new observation and retrain if thresholds are met."""
        self.training_data.append(vehicle_count)
        self.samples_since_last_train += 1

        should_retrain = (
            self.samples_since_last_train >= self.RETRAIN_INTERVAL
            or time.time() - self.last_train_time > 10800  # 3 hours
        )

        if should_retrain:
            self.train()
            self.save_model()

    def train(self):
        """Fit K-means with 3 clusters on rolling window data."""
        if len(self.training_data) < self.MIN_SAMPLES:
            return

        try:
            X = np.array(list(self.training_data), dtype=np.float32).reshape(-1, 1)

            self.model = KMeans(
                n_clusters=3,
                random_state=42,
                n_init=5,
                max_iter=50
            )
            self.model.fit(X)

            centers = self.model.cluster_centers_.flatten()
            sorted_indices = np.argsort(centers)
            self.label_mapping = {int(old): int(new) for new, old in enumerate(sorted_indices)}
            self.cluster_centers = np.sort(centers)

            self.samples_since_last_train = 0
            self.last_train_time = time.time()
            self.is_trained = True

            print(f"✓ K-means trained | Centers: {self.cluster_centers.round(1)}")
            gc.collect()

        except Exception as e:
            print(f"✗ K-means training error: {e}")

    def classify(self, vehicle_count):
        """
        Classify vehicle count into a density band.
        Returns (cluster_index, density_label) where cluster 0=LOW, 1=MEDIUM, 2=HIGH.
        """
        if not self.is_trained or self.model is None:
            return self._fallback_classification(vehicle_count)

        try:
            raw_cluster = int(self.model.predict([[vehicle_count]])[0])
            cluster = self.label_mapping[raw_cluster]
            density_labels = {0: "LOW", 1: "MEDIUM", 2: "HIGH"}
            return cluster, density_labels[cluster]
        except Exception as e:
            print(f"✗ Classification error: {e}")
            return self._fallback_classification(vehicle_count)

    def _fallback_classification(self, vehicle_count):
        """Rule-based fallback before the model is ready."""
        if vehicle_count <= 5:
            return 0, "LOW"
        elif vehicle_count <= 12:
            return 1, "MEDIUM"
        else:
            return 2, "HIGH"

    def save_model(self):
        """Persist the current model to disk."""
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
            print("✓ K-means model saved")
        except Exception as e:
            print(f"✗ Model save error: {e}")

    def load_model(self):
        """Load a previously saved model from disk."""
        try:
            with open('models/traffic_kmeans.pkl', 'rb') as f:
                model_data = pickle.load(f)
                self.model = model_data['model']
                self.cluster_centers = model_data['cluster_centers']
                self.label_mapping = model_data['label_mapping']
                self.is_trained = True
                print(f"✓ K-means model loaded | Centers: {self.cluster_centers.round(1)}")
        except FileNotFoundError:
            print("○ No saved K-means model found — will train from seed data")
        except Exception as e:
            print(f"✗ Model load error: {e}")

    def get_stats(self):
        """Return current model statistics as a dict."""
        return {
            "trained": self.is_trained,
            "samples_collected": len(self.training_data),
            "cluster_centers": self.cluster_centers.tolist() if self.cluster_centers is not None else None,
            "samples_since_retrain": self.samples_since_last_train,
            "next_retrain_in": self.RETRAIN_INTERVAL - self.samples_since_last_train
        }


# Initialize systems
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
# Error / Placeholder Frame
# ---------------------------
def make_placeholder_frame(message="No camera available"):
    """Generate a dark placeholder JPEG frame with a status message."""
    frame = np.zeros((360, 480, 3), dtype=np.uint8)
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
# Video Processing Generator
# ---------------------------
frame_counter = 0


def process_frame():
    """
    Main video generator.
    Reads frames, runs ONNX inference, updates K-means,
    drives signal logic, and yields MJPEG chunks.
    """
    global cap, is_video_file, frame_counter

    if cap is None:
        print("ERROR: No video source initialized")
        while True:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n'
                   + make_placeholder_frame("Initializing video source...") + b'\r\n')
            time.sleep(1)
        return

    print("Starting video feed stream...")
    consecutive_failures = 0

    while True:
        try:
            ret, frame = cap.read()

            if not ret or frame is None or frame.size == 0:
                consecutive_failures += 1
                if consecutive_failures >= 10:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n'
                           + make_placeholder_frame("Video source error") + b'\r\n')
                    time.sleep(1)
                    consecutive_failures = 0
                else:
                    time.sleep(0.05)
                continue

            consecutive_failures = 0
            frame_counter += 1

            # Skip every other frame to halve CPU load
            if frame_counter % 2 != 0:
                time.sleep(0.033)
                continue

            # --- Detection ---
            # Use real ONNX inference for physical camera,
            # use position-based count for synthetic (YOLO can't detect drawn rects)
            if isinstance(cap, SyntheticVideoGenerator):
                vehicles = detect_vehicles_synthetic(cap)
            else:
                vehicles = detect_vehicles(frame)
            vehicle_count = len(vehicles)

            # Draw bounding boxes
            for class_id, bbox in vehicles:
                x1, y1, x2, y2 = bbox
                label = VEHICLE_CLASSES[class_id]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # --- K-Means Classification ---
            kmeans_system.add_sample(vehicle_count)
            cluster, density = kmeans_system.classify(vehicle_count)

            traffic_state["vehicle_count"] = vehicle_count
            traffic_state["traffic_density"] = density
            traffic_state["cluster"] = cluster

            # --- Signal Logic ---
            current_time = time.time()
            elapsed_time = current_time - traffic_state["last_change"]

            if elapsed_time >= traffic_state["timer"]:
                if traffic_state["signal"] == "red":
                    if density == "HIGH":
                        traffic_state["signal"] = "green"
                        traffic_state["timer"] = 20
                    elif density == "MEDIUM":
                        traffic_state["signal"] = "yellow"
                        traffic_state["timer"] = 8
                    else:
                        traffic_state["signal"] = "red"
                        traffic_state["timer"] = 10
                elif traffic_state["signal"] == "green":
                    traffic_state["signal"] = "yellow"
                    traffic_state["timer"] = 4
                elif traffic_state["signal"] == "yellow":
                    traffic_state["signal"] = "red"
                    traffic_state["timer"] = 10

                traffic_state["last_change"] = current_time

            # --- Overlay ---
            signal_colors = {"red": (0, 0, 255), "yellow": (0, 255, 255), "green": (0, 255, 0)}
            density_colors = {"LOW": (0, 255, 0), "MEDIUM": (0, 255, 255), "HIGH": (0, 0, 255)}

            cv2.putText(frame, f"Signal: {traffic_state['signal'].upper()}",
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        signal_colors.get(traffic_state["signal"], (255, 255, 255)), 2)
            cv2.putText(frame, f"Vehicles: {vehicle_count}",
                        (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(frame, f"Density: {density}",
                        (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                        density_colors.get(density, (255, 255, 255)), 2)

            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
            frame_bytes = buffer.tobytes()
            del buffer

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            if frame_counter % 50 == 0:
                gc.collect()

            time.sleep(0.1)  # ~10 fps

        except Exception as e:
            print(f"Error in video processing: {e}")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n'
                   + make_placeholder_frame(f"Error: {str(e)}") + b'\r\n')
            time.sleep(1)


# ---------------------------
# Flask Routes
# ---------------------------

@app.route('/video_feed')
def video_feed():
    return Response(process_frame(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video_feed_raw')
def video_feed_raw():
    """Raw video feed without ONNX inference — useful for debugging camera."""
    def generate_raw():
        print("Starting RAW video feed (no inference)...")
        frame_count = 0
        while True:
            try:
                if cap is None:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n'
                           + make_placeholder_frame("No video source") + b'\r\n')
                    time.sleep(1)
                    continue

                ret, frame = cap.read()
                if not ret or frame is None:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n'
                           + make_placeholder_frame("Frame read error") + b'\r\n')
                    time.sleep(0.1)
                    continue

                frame_count += 1
                cv2.putText(frame, f"Frame: {frame_count}", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                time.sleep(0.1)

            except Exception as e:
                print(f"Raw video error: {e}")
                time.sleep(1)

    return Response(generate_raw(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/test_video')
def test_video():
    """Test endpoint — verifies video source is working."""
    try:
        if cap is None:
            return jsonify({"status": "error", "message": "No video source initialized"})
        ret, frame = cap.read()
        if not ret or frame is None:
            return jsonify({"status": "error", "message": "Failed to read frame"})
        return jsonify({
            "status": "success",
            "message": "Video source working",
            "frame_shape": list(frame.shape),
            "is_synthetic": isinstance(cap, SyntheticVideoGenerator),
            "vehicle_positions": len(cap.vehicle_positions) if isinstance(cap, SyntheticVideoGenerator) else None
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})


@app.route('/traffic_status')
def traffic_status():
    """Current traffic signal state and K-means classification."""
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
    """Detailed K-means model statistics."""
    return jsonify(kmeans_system.get_stats())


@app.route('/train_model', methods=['POST'])
def train_model():
    """Manually trigger K-means retraining."""
    kmeans_system.train()
    kmeans_system.save_model()
    return jsonify({
        "status": "success",
        "message": "Model retrained successfully",
        "stats": kmeans_system.get_stats()
    })


# Serve React SPA for all non-API routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


# ---------------------------
# Startup
# ---------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("AI Traffic Control System — ONNX Runtime Edition")
    print("Memory Optimized for 512MB RAM")
    print("=" * 50)
    video_source = "Synthetic (Cloud Mode)" if isinstance(cap, SyntheticVideoGenerator) else "Physical Camera"
    print(f"Video Source  : {video_source}")
    print(f"Inference     : ONNX Runtime (CPU) | {INPUT_SIZE}x{INPUT_SIZE}")
    print(f"Classification: K-Means (3 clusters)")
    print(f"Resolution    : 480x360 @ ~10 fps")
    print("=" * 50)

    try:
        app.run(debug=False, threaded=True, host='0.0.0.0', port=5000)
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        print("Shutdown complete.")
