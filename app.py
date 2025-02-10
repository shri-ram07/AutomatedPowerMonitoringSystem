import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QGridLayout, QFrame, QMessageBox
from PyQt5.QtGui import QImage, QPixmap, QFont, QLinearGradient, QColor, QBrush, QPainter
from PyQt5.QtCore import QTimer, Qt
from pyfirmata import Arduino

# Initialize Arduino board
board = Arduino('COM1')  # Update with your Arduino port
pins = {
    0: board.get_pin('d:13:o'),  # Point 0.1
    1: board.get_pin('d:12:o'),  # Point 0.2
    2: board.get_pin('d:11:o'),  # Point 0.3
    3: board.get_pin('d:10:o')   # Point 0.4
}

# Load YOLOv3 model
net = cv2.dnn.readNetFromDarknet('yolov3.cfg', 'yolov3.weights')
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

cap = cv2.VideoCapture(0)

# Default corner points (fallback if user doesn't set them)
DEFAULT_CORNER_POINTS = [(520, 108), (105, 214), (820, 255), (517, 591)]

# Global variables for statistics
total_people = 0
electricity_saved = 0
automatic_mode = True  # Start in Automatic Mode


class GradientBackground(QWidget):
    """Custom widget to draw gradient backgrounds."""
    def __init__(self, color1, color2, parent=None):
        super().__init__(parent)
        self.color1 = color1
        self.color2 = color2

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, self.color1)
        gradient.setColorAt(1.0, self.color2)
        painter.fillRect(event.rect(), QBrush(gradient))


class SetupWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Setup Corner Points")
        self.setGeometry(100, 100, 800, 600)

        # Set gradient background
        self.background = GradientBackground(QColor("#f0f8ff"), QColor("#c6e2ff"), self)
        self.background.setGeometry(self.rect())

        self.layout = QVBoxLayout(self)

        # Video Feed Section
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; border-radius: 10px;")
        self.layout.addWidget(self.video_label)

        # Instructions Label
        self.instructions_label = QLabel("Click on the video feed to set the 4 corner points.", self)
        self.instructions_label.setStyleSheet("font-size: 16px; color: #333;")
        self.instructions_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.instructions_label)

        # Save Button
        self.save_button = QPushButton("Save and Proceed", self)
        self.save_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #007bff, stop: 1 #0056b3);
                color: white;
                font-size: 16px;
                padding: 10px;
                border-radius: 5px;
                transition: background 0.3s ease;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #0056b3, stop: 1 #004085);
            }
        """)
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_and_proceed)
        self.layout.addWidget(self.save_button)

        # Timer for video feed updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_video_feed)
        self.timer.start(30)  # Update every 30ms

        # Variables for point selection
        self.corner_points = []
        self.click_count = 0

    def update_video_feed(self):
        success, image = cap.read()
        if not success:
            return

        # Draw existing points on the video feed
        for point in self.corner_points:
            cv2.circle(image, point, 10, (0, 255, 0), -1)

        # Convert image to PyQt-compatible format
        h, w, ch = image.shape
        bytes_per_line = ch * w
        qt_image = QImage(image.data, w, h, bytes_per_line, QImage.Format_BGR888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))

    def mousePressEvent(self, event):
        if len(self.corner_points) < 4:
            x, y = event.pos().x(), event.pos().y()

            # Map the click position to the video resolution
            video_width = self.video_label.width()
            video_height = self.video_label.height()
            frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            mapped_x = int(x / video_width * frame_width)
            mapped_y = int(y / video_height * frame_height)

            self.corner_points.append((mapped_x, mapped_y))
            self.click_count += 1

            if self.click_count == 4:
                self.save_button.setEnabled(True)
                self.instructions_label.setText("All 4 points set! Click 'Save and Proceed'.")

    def save_and_proceed(self):
        global corner_points
        corner_points = self.corner_points
        self.close()
        self.main_window = MainWindow(corner_points)
        self.main_window.show()


class MainWindow(QMainWindow):
    def __init__(self, corner_points):
        super().__init__()

        self.setWindowTitle("Smart Room Monitoring")
        self.setGeometry(100, 100, 1200, 800)

        # Set gradient background
        self.background = GradientBackground(QColor("#f0f8ff"), QColor("#c6e2ff"), self)
        self.background.setGeometry(self.rect())

        # Main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QGridLayout(self.central_widget)

        # Video Feed Section
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; border-radius: 10px;")
        self.layout.addWidget(self.video_label, 0, 0, 1, 2)

        # Mode Toggle Section
        self.mode_toggle_frame = QFrame(self)
        self.mode_toggle_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 10px;
                padding: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
        """)
        self.mode_toggle_layout = QVBoxLayout(self.mode_toggle_frame)

        self.mode_toggle_button = QPushButton("Switch to Manual Mode", self)
        self.mode_toggle_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #007bff, stop: 1 #0056b3);
                color: white;
                font-size: 16px;
                padding: 10px;
                border-radius: 5px;
                transition: background 0.3s ease;
            }
            QPushButton:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #0056b3, stop: 1 #004085);
            }
        """)
        self.mode_toggle_button.clicked.connect(self.toggle_mode)
        self.mode_toggle_layout.addWidget(self.mode_toggle_button)

        self.layout.addWidget(self.mode_toggle_frame, 1, 0)

        # Manual Switch Controller Section
        self.switch_frame = QFrame(self)
        self.switch_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 10px;
                padding: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
        """)
        self.switch_layout = QVBoxLayout(self.switch_frame)
        self.switch_buttons = []

        for i in range(4):
            btn = QPushButton(f"Switch {i+1} (OFF)", self)
            btn.setCheckable(True)  # Make the button toggleable
            btn.clicked.connect(lambda _, i=i: self.toggle_manual_switch(i))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ccc;
                    color: black;
                    font-size: 14px;
                    padding: 10px;
                    border-radius: 5px;
                    transition: background-color 0.3s ease;
                }
                QPushButton:checked {
                    background-color: #28a745;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
            """)
            btn.setEnabled(False)  # Disable buttons in Automatic Mode
            self.switch_layout.addWidget(btn)
            self.switch_buttons.append(btn)

        self.layout.addWidget(self.switch_frame, 1, 1)

        # Statistics Section
        self.stats_label = QLabel("Total People: 0\nElectricity Saved: 0 kWh\nAppliances Count: 0", self)
        self.stats_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #333;
                background-color: #ffffff;
                border-radius: 10px;
                padding: 10px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
        """)
        self.stats_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.stats_label, 2, 0, 1, 2)

        # Timer for video feed updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_video_feed)
        self.timer.start(30)  # Update every 30ms

        # Global variables
        self.total_people = 0
        self.electricity_saved = 0
        self.corner_points = corner_points

    def toggle_mode(self):
        global automatic_mode
        automatic_mode = not automatic_mode

        if automatic_mode:
            self.mode_toggle_button.setText("Switch to Manual Mode")
            for btn in self.switch_buttons:
                btn.setEnabled(False)  # Disable manual buttons
        else:
            self.mode_toggle_button.setText("Switch to Automatic Mode")
            for btn in self.switch_buttons:
                btn.setEnabled(True)  # Enable manual buttons

    def toggle_manual_switch(self, switch_id):
        current_state = pins[switch_id].read()
        pins[switch_id].write(1 if current_state == 0 else 0)
        self.switch_buttons[switch_id].setText(f"Switch {switch_id+1} ({'ON' if current_state == 0 else 'OFF'})")

    def update_video_feed(self):
        global total_people, electricity_saved, automatic_mode

        success, image = cap.read()
        if not success:
            return

        small_image = cv2.resize(image, (608, 608))
        blob = cv2.dnn.blobFromImage(small_image, 1/255.0, (608, 608), swapRB=True, crop=False)
        net.setInput(blob)
        layer_names = net.getLayerNames()
        output_layers = [layer_names[i - 1] for i in net.getUnconnectedOutLayers()]
        detections = net.forward(output_layers)

        height, width, _ = image.shape
        boxes = []
        confidences = []
        class_ids = []

        for detection in detections:
            for obj in detection:
                scores = obj[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                if class_id == 0 and confidence > 0.5:  # Class 0 is 'person'
                    box = obj[0:4] * np.array([width, height, width, height])
                    (x_center, y_center, w, h) = box.astype("int")
                    x_min = int(x_center - (w / 2))
                    y_min = int(y_center - (h / 2))
                    boxes.append([x_min, y_min, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)

        indices = cv2.dnn.NMSBoxes(boxes, confidences, 0.5, 0.4)
        nearest_points = set()

        if len(indices) > 0:
            for i in indices.flatten():
                box = boxes[i]
                x_min, y_min, w, h = box
                x_max = x_min + w
                y_max = y_min + h
                x_center = (x_min + x_max) // 2
                y_center = (y_min + y_max) // 2

                distances = [np.linalg.norm(np.array([x_center, y_center]) - np.array(point)) for point in self.corner_points]
                nearest_point_index = np.argmin(distances)
                nearest_points.add(nearest_point_index)

                # Draw bounding box and label
                label = f'Person {confidences[i]:.2f}'
                cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (255, 0, 0), 2)
                cv2.putText(image, label, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                cv2.putText(image, f'Nearest Point: {nearest_point_index + 1}', (x_min, y_min - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                cv2.circle(image, self.corner_points[nearest_point_index], 10, (0, 255, 0), -1)

            # Update total people count
            self.total_people = len(indices)

        # Control appliances based on mode
        if automatic_mode:
            for i in range(4):
                pins[i].write(0 if i in nearest_points else 1)

        # Calculate electricity saved (example logic)
        self.electricity_saved += self.total_people * 0.1  # Example: 0.1 kWh per person

        # Convert image to PyQt-compatible format
        h, w, ch = image.shape
        bytes_per_line = ch * w
        qt_image = QImage(image.data, w, h, bytes_per_line, QImage.Format_BGR888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))

        # Update statistics labels
        self.stats_label.setText(f"Total People: {self.total_people}\nElectricity Saved: {round(self.electricity_saved, 2)} kWh\nAppliances Count: {len(pins)}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    setup_window = SetupWindow()
    setup_window.show()
    sys.exit(app.exec_())

    # Release resources when the application closes
    cap.release()