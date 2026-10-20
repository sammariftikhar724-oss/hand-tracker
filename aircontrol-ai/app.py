# app.py
import math
import time
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from flask import Flask, Response, jsonify, render_template, request

from brightness_control import set_brightness
from volume_control import mouse_control, set_volume

app = Flask(__name__)

APP_DIR = Path(__file__).resolve().parent
MODEL_PATH = APP_DIR / "models" / "hand_landmarker.task"

# Global States
current_mode = "Volume Control"
min_dist = 30
max_dist = 140
draw_color = (255, 0, 255)
brush_thickness = 8
clear_canvas_requested = False

canvas = None
xp, yp = 0, 0
landmarker = None

def init_landmarker():
    global landmarker
    try:
        if not MODEL_PATH.is_file():
            print(f"[ERROR] Hand model not found at {MODEL_PATH}")
            return
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision

        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(MODEL_PATH)),
            running_mode=vision.RunningMode.IMAGE,
            num_hands=1,
            min_hand_detection_confidence=0.6,
            min_hand_presence_confidence=0.6,
            min_tracking_confidence=0.6,
        )
        landmarker = vision.HandLandmarker.create_from_options(options)
        print("[INFO] MediaPipe HandLandmarker initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize MediaPipe: {e}")

init_landmarker()

def calculate_distance(pt1, pt2):
    return math.hypot(pt1[0] - pt2[0], pt1[1] - pt2[1])

def distance_to_percent(distance, minimum, maximum):
    if maximum <= minimum:
        return 0
    ratio = (distance - minimum) / (maximum - minimum)
    return int(max(0, min(100, ratio * 100)))

def generate_frames():
    global canvas, xp, yp, clear_canvas_requested
    
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    last_control_time = 0.0
    last_control_value = None
    last_click_time = 0.0
    
    smooth_x, smooth_y = 0, 0
    alpha = 0.6

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        h, w, c = frame.shape

        if canvas is None or clear_canvas_requested:
            canvas = np.zeros((h, w, 3), dtype=np.uint8)
            clear_canvas_requested = False

        if landmarker:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb_frame,
            )
            try:
                result = landmarker.detect(mp_image)
                if result.hand_landmarks:
                    for hand_landmarks in result.hand_landmarks:
                        points = [
                            (
                                max(0, min(w - 1, int(p.x * w))),
                                max(0, min(h - 1, int(p.y * h))),
                            )
                            for p in hand_landmarks
                        ]

                        from mediapipe.tasks.python import vision
                        for conn in vision.HandLandmarksConnections.HAND_CONNECTIONS:
                            start_idx = conn.start if hasattr(conn, 'start') else conn[0]
                            end_idx = conn.end if hasattr(conn, 'end') else conn[1]
                            cv2.line(frame, points[start_idx], points[end_idx], (147, 51, 234), 2, cv2.LINE_AA)
                            
                        for pt in points:
                            cv2.circle(frame, pt, 3, (56, 189, 248), -1, cv2.LINE_AA)

                        thumb_tip = points[4]
                        raw_index_tip = points[8]
                        distance = calculate_distance(thumb_tip, raw_index_tip)

                        if smooth_x == 0 and smooth_y == 0:
                            smooth_x, smooth_y = raw_index_tip
                        else:
                            smooth_x = int(alpha * raw_index_tip[0] + (1 - alpha) * smooth_x)
                            smooth_y = int(alpha * raw_index_tip[1] + (1 - alpha) * smooth_y)
                        
                        index_tip = (smooth_x, smooth_y)

                        # Glowing tracking circle
                        cv2.circle(frame, index_tip, 12, (0, 255, 255), 2, cv2.LINE_AA)
                        cv2.circle(frame, index_tip, 4, (0, 0, 255), -1, cv2.LINE_AA)

                        if current_mode == "Air Drawing":
                            if distance < 35:
                                xp, yp = index_tip
                                cv2.circle(frame, index_tip, 15, (0, 0, 255), cv2.FILLED)
                            else:
                                if xp == 0 and yp == 0:
                                    xp, yp = index_tip
                                if draw_color == (0, 0, 0):
                                    cv2.line(canvas, (xp, yp), index_tip, (0, 0, 0), brush_thickness * 3)
                                    cv2.circle(frame, index_tip, (brush_thickness * 3) // 2, (255, 255, 255), 1)
                                else:
                                    cv2.line(canvas, (xp, yp), index_tip, draw_color, brush_thickness)
                                xp, yp = index_tip

                        elif current_mode in ("Volume Control", "Brightness Control"):
                            now = time.monotonic()
                            if now - last_control_time >= 0.2:
                                val = distance_to_percent(distance, min_dist, max_dist)
                                if last_control_value is None or abs(val - last_control_value) >= 2:
                                    try:
                                        if current_mode == "Volume Control":
                                            set_volume(val)
                                        else:
                                            set_brightness(val)
                                        last_control_value = val
                                        last_control_time = now
                                    except Exception:
                                        pass

                        elif current_mode == "Air Mouse":
                            # Move mouse cursor
                            mouse_control("move", index_tip[0], index_tip[1])
                            # Click if pinch
                            if distance < 30:
                                now = time.monotonic()
                                if now - last_click_time > 0.6:
                                    mouse_control("click")
                                    last_click_time = now
                                    cv2.putText(frame, "CLICK!", (50, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            except Exception as e:
                print(f"Tracking error: {e}")

        if current_mode == "Air Drawing" and canvas is not None:
            gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
            _, inv = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY_INV)
            inv = cv2.cvtColor(inv, cv2.COLOR_GRAY2BGR)
            frame = cv2.bitwise_and(frame, inv)
            frame = cv2.bitwise_or(frame, canvas)

        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    cap.release()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/update_settings', methods=['POST'])
def update_settings():
    global current_mode, min_dist, max_dist, draw_color, brush_thickness, clear_canvas_requested
    data = request.json
    current_mode = data.get('mode', current_mode)
    min_dist = int(data.get('min_dist', min_dist))
    max_dist = int(data.get('max_dist', max_dist))
    brush_thickness = int(data.get('brush_thickness', brush_thickness))
    
    if data.get('clear_canvas'):
        clear_canvas_requested = True

    hex_col = data.get('color', '#FF00FF')
    if hex_col == 'eraser':
        draw_color = (0, 0, 0)
    else:
        h_col = hex_col.lstrip('#')
        rgb = tuple(int(h_col[i:i+2], 16) for i in (0, 2, 4))
        draw_color = (rgb[2], rgb[1], rgb[0])

    return jsonify(success=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)