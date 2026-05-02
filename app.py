from flask import Flask, render_template, Response, jsonify, send_from_directory
from flask_cors import CORS
import cv2
import time
import torch
import numpy as np
import os

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
    "vehicle_count": 0
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

        # Traffic light logic
        current_time = time.time()
        elapsed_time = current_time - traffic_state["last_change"]

        if elapsed_time >= traffic_state["timer"]:
            if traffic_state["signal"] == "red":
                if vehicle_count >= 10:
                    traffic_state["signal"] = "green"
                    traffic_state["timer"] = 15
                elif vehicle_count >= 5:
                    traffic_state["signal"] = "yellow"
                    traffic_state["timer"] = 10
                else:
                    traffic_state["signal"] = "red"
                    traffic_state["timer"] = 15
            elif traffic_state["signal"] == "green":
                traffic_state["signal"] = "yellow"
                traffic_state["timer"] = 4
            elif traffic_state["signal"] == "yellow":
                traffic_state["signal"] = "red"
                traffic_state["timer"] = 15

            traffic_state["last_change"] = current_time

        traffic_state["vehicle_count"] = vehicle_count

        # Overlay text on frame
        signal_colors = {"red": (0, 0, 255), "yellow": (0, 255, 255), "green": (0, 255, 0)}
        sig_color = signal_colors.get(traffic_state["signal"], (255, 255, 255))
        cv2.putText(frame, f"Signal: {traffic_state['signal'].upper()}",
                    (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, sig_color, 2)
        cv2.putText(frame, f"Vehicles: {vehicle_count}",
                    (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

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


@app.route('/traffic_status')
def traffic_status():
    return jsonify({
        "traffic_light": traffic_state["signal"],
        "vehicle_count": traffic_state["vehicle_count"]
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
