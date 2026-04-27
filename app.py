from flask import Flask, render_template, Response, jsonify
from flask_cors import CORS
import cv2
import time
import torch
import numpy as np

# Monkey patch torch.load to use weights_only=False
original_load = torch.load
def patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return original_load(*args, **kwargs)
torch.load = patched_load

from ultralytics import YOLO

app = Flask(__name__)
CORS(app)

model = YOLO("models/yolov8n.pt")

# ---------------------------
# Camera Initialization
# ---------------------------
def init_camera():
    for index in [0, 1, 2]:
        cam = cv2.VideoCapture(index, cv2.CAP_DSHOW)  # CAP_DSHOW is faster on Windows
        if cam.isOpened():
            cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cam.set(cv2.CAP_PROP_FPS, 30)

            # Warm up: discard first 5 frames (camera needs time to adjust exposure)
            for _ in range(5):
                cam.read()

            # Verify we actually get a valid frame
            ret, frame = cam.read()
            if ret and frame is not None and frame.size > 0:
                print(f"SUCCESS: Camera {index} opened and returning valid frames. Shape: {frame.shape}")
                return cam
            else:
                print(f"Camera {index} opened but returned empty frame, trying next...")
                cam.release()
        else:
            print(f"Camera index {index} failed to open.")

    print("ERROR: No working camera found!")
    return None

cap = init_camera()

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
# Error Frame Generator
# ---------------------------
def make_error_frame(message="Camera not available"):
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    cv2.putText(frame, message, (60, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    _, buffer = cv2.imencode('.jpg', frame)
    return buffer.tobytes()


# ---------------------------
# Video Processing Generator
# ---------------------------
def process_frame():
    global cap

    if cap is None:
        # Keep sending error frame if no camera
        while True:
            error_bytes = make_error_frame("No camera found")
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + error_bytes + b'\r\n')
            time.sleep(1)
        return

    frame_count = 0
    consecutive_failures = 0

    while True:
        ret, frame = cap.read()

        if not ret or frame is None or frame.size == 0:
            consecutive_failures += 1
            print(f"Frame read failed (attempt {consecutive_failures})")

            if consecutive_failures >= 10:
                print("Too many failures, reinitializing camera...")
                cap.release()
                time.sleep(1)
                cap = init_camera()
                consecutive_failures = 0
                if cap is None:
                    error_bytes = make_error_frame("Camera disconnected")
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + error_bytes + b'\r\n')
                    time.sleep(1)
            else:
                error_bytes = make_error_frame("Reading frame...")
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + error_bytes + b'\r\n')
                time.sleep(0.05)
            continue

        consecutive_failures = 0
        frame_count += 1

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
        cv2.putText(frame, f"Signal: {traffic_state['signal'].upper()}",
                    (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(frame, f"Vehicles: {vehicle_count}",
                    (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        # Encode and yield frame
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')


# ---------------------------
# Flask Routes
# ---------------------------
@app.route('/')
def index():
    return render_template('index.html')


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


# ---------------------------
# Run App
# ---------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("AI Traffic Control System - Starting")
    print("=" * 50)
    print(f"Camera status: {'Ready' if cap is not None else 'NOT FOUND'}")
    print("Flask server: http://localhost:5000")
    print("Video feed:   http://localhost:5000/video_feed")
    print("=" * 50)

    try:
        app.run(debug=False, threaded=True, host='0.0.0.0', port=5000)
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        print("Shutdown complete.")
