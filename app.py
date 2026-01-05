from flask import Flask, render_template, Response, jsonify
import cv2
from ultralytics import YOLO
import time

app = Flask(__name__)
model = YOLO("models/yolov8n.pt")

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

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
# Video Processing Generator
# ---------------------------
def process_frame():
    while True:
        cap.grab()
        ret, frame = cap.read()
        if not ret:
            break

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

        # Display on frame
        cv2.putText(frame, f"Signal: {traffic_state['signal']}",
                    (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        cv2.putText(frame, f"Vehicle Count: {vehicle_count}",
                    (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        # Encode frame
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
    try:
        app.run(debug=True, threaded=True)
    finally:
        cap.release()
        cv2.destroyAllWindows()
