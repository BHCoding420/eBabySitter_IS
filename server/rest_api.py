from flask import Flask, Response, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import cv2
import pygame
import os
import random

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")  # Allow all origins for WebSocket

show_camera = False

# Initialize pygame mixer for playing audio
pygame.mixer.init()

# Load pre-trained face detection model
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def generate_camera_frames():
    camera = cv2.VideoCapture(0)   # Use 0 for default camera, or replace with camera index if multiple cameras are available
    while True:
        if show_camera:
            success, frame = camera.read()
            if not success:
                break

            # Convert frame to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Detect faces in the grayscale frame
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            # Draw bounding boxes around detected faces
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)

            # Encode frame to JPEG format for streaming
            ret, jpeg = cv2.imencode('.jpg', frame)
            frame_bytes = jpeg.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

            # Send a message to the client if no faces are detected
            if len(faces) == 0:
                socketio.emit('no_face_detected', {'message': 'No face detected'})
        else:
            # Send a placeholder image when camera is off
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + open('placeholder.jpg', 'rb').read() + b'\r\n')

@app.route('/api/data')
def get_data():
    data = {'message': 'Hello from Python server!'}
    return jsonify(data)

@app.route('/api/show-camera', methods=['POST'])
def toggle_camera():
    global show_camera
    show_camera = True
    return jsonify({'success': True})

@app.route('/api/turn-off-camera', methods=['POST'])
def turn_off_camera():
    global show_camera
    show_camera = False
    return jsonify({'success': True})

@app.route('/api/camera-feed')
def camera_feed():
    return Response(generate_camera_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/play-song', methods=['POST'])
def play_song():
    sounds_dir = os.path.join(os.path.dirname(__file__), 'sounds')
    songs = [os.path.join(sounds_dir, song) for song in os.listdir(sounds_dir) if song.endswith('.mp3')]

    if not songs:
        return jsonify({'success': False, 'message': 'No songs found in sounds directory'})

    song_to_play = random.choice(songs)
    pygame.mixer.music.load(song_to_play)
    pygame.mixer.music.play()

    return jsonify({'success': True, 'song': os.path.basename(song_to_play)})

@app.route('/api/stop-song', methods=['POST'])
def stop_song():
    pygame.mixer.music.stop()
    return jsonify({'success': True})

if __name__ == '__main__':
    socketio.run(app, debug=True)
