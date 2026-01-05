from flask import Flask, render_template, Response, jsonify
import cv2
from ultralytics import YOLO
import numpy as np

app = Flask(__name__)

# Replace with your mobile camera's stream URL
MOBILE_CAM_URL = "http://192.168.229.229:8080/video"  # Use IP Webcam app to

# Load YOLO model
model = YOLO("yolov8n.pt")  # Ensure you have the YOLOv8 model downloaded

# Reduce frame processing rate
FRAME_SKIP = 3  # Process every 3rd frame for better performance

# Reduce resolution for faster processing
FRAME_WIDTH = 480
FRAME_HEIGHT = 360

def generate_frames():
    cap = cv2.VideoCapture(MOBILE_CAM_URL)
    frame_count = 0
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        
        frame_count += 1
        if frame_count % FRAME_SKIP != 0:
            continue  # Skip frames to reduce processing load
        
        # Resize frame for faster processing
        frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
        
        # Perform vehicle detection
        results = model(frame, verbose=False)
        vehicle_count = 0
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = box.conf[0].item()
                class_id = int(box.cls[0].item())
                label = f"{result.names[class_id]}: {conf:.2f}"
                
                if result.names[class_id] in ["car", "truck", "bus", "motorbike"]:
                    vehicle_count += 1
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Determine traffic signal color
        if vehicle_count < 5:
            traffic_signal = "red"
        elif 5 <= vehicle_count <= 15:
            traffic_signal = "yellow"
        else:
            traffic_signal = "green"

        # Overlay traffic signal on the frame
        cv2.putText(frame, f"Signal: {traffic_signal}", (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    cap.release()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/traffic_status')
def traffic_status():
    cap = cv2.VideoCapture(MOBILE_CAM_URL)
    ret, frame = cap.read()
    if not ret:
        return jsonify({"error": "No frame captured"})
    
    # Resize frame for faster processing
    frame = cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))
    
    # Process the frame
    results = model(frame, verbose=False)
    vehicle_count = sum(1 for result in results for box in result.boxes if result.names[int(box.cls[0].item())] in ["car", "truck", "bus", "motorbike"])

    # Determine traffic signal color
    if vehicle_count < 5:
        traffic_signal = "red"
    elif 5 <= vehicle_count <= 9:
        traffic_signal = "yellow"
    else:
        traffic_signal = "green"
    
    cap.release()
    return jsonify({"traffic_light": traffic_signal, "vehicle_count": vehicle_count})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
