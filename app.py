import os
import time
import random
import threading
import numpy as np
from flask import Flask, Response, jsonify, send_from_directory
from flask_cors import CORS

# ---------------------------
# Mode Detection
# DEMO_MODE=true  → no PyTorch/YOLO loaded, simulated vehicle counts (~150MB RAM)
# DEMO_MODE=false → full YOLO detection (~500MB RAM, needs Starter plan)
# ---------------------------
DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"

if not DEMO_MODE:
    import torch
    import cv2

    # Suppress torch.load warning
    _orig_load = torch.load
    def _patched_load(*args, **kwargs):
        kwargs['weights_only'] = False
        return _orig_load(*args, **kwargs)
    torch.load = _patched_load

    from ultralytics import YOLO
    # Load model once at startup, keep on CPU to save memory
    model = YOLO("models/yolov8n.pt")
    model.to("cpu")
    print("YOLO model loaded on CPU")
else:
    import cv2  # still needed for video/frame encoding
    model = None
    print("DEMO MODE: YOLO skipped — using simulated vehicle counts")

# ---------------------------
# Flask App
# ---------------------------
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'dist')
app = Flask(__name__, static_folder=STATIC_FOLDER, static_url_path='')
CORS(app)

VEHICLE_CLASSES = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}

# Shared traffic state (thread-safe reads are fine for this use case)
traffic_state = {
    "signal": "red",
    "timer": 15,
    "last_change": time.time(),
    "vehicle_count": 0
}

# ---------------------------
# Traffic Logic (runs in background thread)
# Decoupled from video stream so logic keeps ticking even if no viewers
# ---------------------------
def traffic_logic_loop():
    while True:
        time.sleep(1)
        current_time = time.time()
        elapsed = current_time - traffic_state["last_change"]
        count = traffic_state["vehicle_count"]

        if elapsed >= traffic_state["timer"]:
            sig = traffic_state["signal"]
            if sig == "red":
                if count >= 10:
                    traffic_state["signal"] = "green"
                    traffic_state["timer"] = 15
                elif count >= 5:
                    traffic_state["signal"] = "yellow"
                    traffic_state["timer"] = 10
                else:
                    traffic_state["signal"] = "red"
                    traffic_state["timer"] = 15
            elif sig == "green":
                traffic_state["signal"] = "yellow"
                traffic_state["timer"] = 4
            elif sig == "yellow":
                traffic_state["signal"] = "red"
                traffic_state["timer"] = 15

            traffic_state["last_change"] = current_time

threading.Thread(target=traffic_logic_loop, daemon=True).start()

# ---------------------------
# Demo Mode: Simulated vehicle count (no camera/YOLO needed)
# ---------------------------
def simulate_vehicle_count():
    """Smoothly oscillate vehicle count to mimic real traffic patterns."""
    base = random.randint(3, 12)
    noise = random.randint(-2, 2)
    count = max(0, base + noise)
    traffic_state["vehicle_count"] = count
    return count

# ---------------------------
# Camera / Video Initialization
# ---------------------------
def init_capture():
    video_path = os.environ.get("VIDEO_SOURCE", "demo_traffic.mp4")
    if os.path.exists(video_path):
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            print(f"Video source: {video_path}")
            return cap, True

    # Try webcam (local dev only)
    for index in [0, 1, 2]:
        cam = cv2.VideoCapture(index)
        if cam.isOpened():
            cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            for _ in range(3):
                cam.read()
            ret, frame = cam.read()
            if ret and frame is not None:
                print(f"Webcam {index} ready")
                return cam, False
            cam.release()

    print("No video/camera found — placeholder mode")
    return None, False

cap, is_video_file = init_capture()

# ---------------------------
# Vehicle Detection (full mode only)
# ---------------------------
def detect_vehicles(frame):
    # Resize to 320x320 for faster inference (vs default 640)
    small = cv2.resize(frame, (320, 320))
    rgb = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
    results = model(rgb, imgsz=320, verbose=False)[0]

    scale_x = frame.shape[1] / 320
    scale_y = frame.shape[0] / 320
    vehicles = []

    for box in results.boxes:
        class_id = int(box.cls[0])
        if class_id in VEHICLE_CLASSES:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            # Scale coords back to original frame size
            vehicles.append((
                class_id,
                (int(x1 * scale_x), int(y1 * scale_y),
                 int(x2 * scale_x), int(y2 * scale_y))
            ))
    return vehicles

# ---------------------------
# Placeholder Frame Generator
# ---------------------------
def make_placeholder_frame(message="Demo Mode — No Video Source"):
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    for i in range(0, 640, 40):
        cv2.line(frame, (i, 0), (i, 480), (20, 20, 20), 1)
    for i in range(0, 480, 40):
        cv2.line(frame, (0, i), (640, i), (20, 20, 20), 1)

    sig = traffic_state["signal"]
    sig_colors = {"red": (0, 0, 255), "yellow": (0, 255, 255), "green": (0, 255, 0)}
    color = sig_colors.get(sig, (255, 255, 255))

    cv2.putText(frame, f"Signal: {sig.upper()}", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    cv2.putText(frame, f"Vehicles: {traffic_state['vehicle_count']}", (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
    cv2.putText(frame, message, (60, 260),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 180, 255), 2)
    cv2.putText(frame, "AI Traffic Control System", (110, 300),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1)

    _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return buffer.tobytes()

# ---------------------------
# Frame Generator
# ---------------------------
# Run YOLO only every N frames to reduce CPU load
DETECT_EVERY_N_FRAMES = int(os.environ.get("DETECT_EVERY_N", "5"))
# Target FPS for streaming
STREAM_FPS = float(os.environ.get("STREAM_FPS", "10"))
FRAME_DELAY = 1.0 / STREAM_FPS

def process_frame():
    global cap, is_video_file
    frame_count = 0
    consecutive_failures = 0

    # No video source — stream placeholder with live traffic state
    if cap is None:
        while True:
            if DEMO_MODE:
                simulate_vehicle_count()
            frame_bytes = make_placeholder_frame()
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                   + frame_bytes + b'\r\n')
            time.sleep(1)
        return

    while True:
        ret, frame = cap.read()

        # Loop video file
        if not ret and is_video_file:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()

        if not ret or frame is None or frame.size == 0:
            consecutive_failures += 1
            if consecutive_failures >= 10:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                       + make_placeholder_frame("Stream interrupted") + b'\r\n')
                time.sleep(1)
                consecutive_failures = 0
            continue

        consecutive_failures = 0
        frame_count += 1

        # --- Vehicle detection ---
        if DEMO_MODE:
            # Simulate count, no YOLO
            if frame_count % DETECT_EVERY_N_FRAMES == 0:
                simulate_vehicle_count()
            vehicle_count = traffic_state["vehicle_count"]
        else:
            # Run YOLO every N frames, reuse last count in between
            if frame_count % DETECT_EVERY_N_FRAMES == 0:
                vehicles = detect_vehicles(frame)
                vehicle_count = len(vehicles)
                traffic_state["vehicle_count"] = vehicle_count
                for class_id, (x1, y1, x2, y2) in vehicles:
                    label = VEHICLE_CLASSES[class_id]
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, label, (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            else:
                vehicle_count = traffic_state["vehicle_count"]

        # Overlay
        sig = traffic_state["signal"]
        sig_colors = {"red": (0, 0, 255), "yellow": (0, 255, 255), "green": (0, 255, 0)}
        cv2.putText(frame, f"Signal: {sig.upper()}", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, sig_colors.get(sig, (255,255,255)), 2)
        cv2.putText(frame, f"Vehicles: {vehicle_count}", (20, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
        if DEMO_MODE:
            cv2.putText(frame, "DEMO MODE", (20, 130),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)

        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
               + buffer.tobytes() + b'\r\n')

        time.sleep(FRAME_DELAY)

# ---------------------------
# Routes
# ---------------------------
@app.route('/video_feed')
def video_feed():
    return Response(process_frame(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/traffic_status')
def traffic_status():
    return jsonify({
        "traffic_light": traffic_state["signal"],
        "vehicle_count": traffic_state["vehicle_count"],
        "demo_mode": DEMO_MODE
    })

# Serve React SPA
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

# ---------------------------
# Entry Point
# ---------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("AI Traffic Control System")
    print(f"Mode:   {'DEMO (simulated)' if DEMO_MODE else 'FULL (YOLO active)'}")
    print(f"Source: {'Video file' if is_video_file else 'Webcam' if cap else 'Placeholder'}")
    print("URL:    http://localhost:5000")
    print("=" * 50)
    try:
        app.run(debug=False, threaded=True, host='0.0.0.0', port=5000)
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
