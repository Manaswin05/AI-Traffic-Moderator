# AI Traffic Controller 🚦

An AI-powered traffic signal control system that uses **computer vision and deep learning (YOLOv8)** to detect vehicles in real time and dynamically manage traffic signals. Built with **Flask, OpenCV, and Ultralytics YOLO**, this project demonstrates how AI can improve traffic flow and reduce congestion.

---

## 🔍 Features

* Real-time vehicle detection using **YOLOv8**
* Supports detection of **cars, motorcycles, buses, and trucks**
* Dynamic traffic signal timing based on vehicle density
* Live video streaming via Flask
* Simple web-based dashboard
* Google Maps–style traffic visualization (HTML-based)
* Includes an alternative **Wireless Type** implementation

---

## 🧠 Technologies Used

* **Python 3**
* **Flask** – Web framework
* **OpenCV** – Video capture and processing
* **YOLOv8 (Ultralytics)** – Object detection model
* **HTML/CSS/JavaScript** – Frontend

---

## 📁 Project Structure

```
AI Traffic Controller/
│
├── app.py                     # Main Flask application
├── maps.html                  # Traffic map visualization
├── README.md                  # Project documentation
├── models/
│   └── yolov8n.pt             # Pre-trained YOLOv8 model
├── templates/
│   └── index.html             # Web interface
│
├── Wireless type/             # Alternative wireless-based setup
│   ├── app.py
│   ├── maps.html
│   ├── models/
│   └── templates/
│       └── index.html
└── .gitignore
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/ai-traffic-controller.git
cd ai-traffic-controller
```

### 2️⃣ Install Dependencies

```bash
pip install flask opencv-python ultralytics
```

> ⚠️ Make sure you have **Python 3.8+** installed.

### 3️⃣ Run the Application

```bash
python app.py
```

### 4️⃣ Open in Browser

Navigate to:

```
http://127.0.0.1:5000
```

---

## 🚗 How It Works

1. Captures live video feed from a webcam
2. Processes each frame using YOLOv8
3. Detects and counts vehicles
4. Adjusts traffic signal timing dynamically
5. Streams annotated video and traffic status to the web UI

---

## 📌 Supported Vehicle Classes

* Car
* Motorcycle
* Bus
* Truck

---

## 🧪 Use Cases

* Smart city traffic management
* Academic and final-year projects
* AI + Computer Vision demonstrations
* Traffic simulation systems

---

## 🚀 Future Improvements

* Multi-camera intersection support
* Emergency vehicle prioritization
* Cloud-based deployment
* Integration with IoT traffic sensors
* Real-time analytics dashboard

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a new branch
3. Commit your changes
4. Submit a pull request

---

## 📜 License

This project is for **educational and research purposes**. Feel free to modify and enhance it.

---

## 👤 Author

Developed by **[Your Name]**
Feel free to connect and contribute!
