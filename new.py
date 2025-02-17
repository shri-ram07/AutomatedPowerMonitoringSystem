import sys
import time

import cv2
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QGridLayout, QFrame, QMessageBox ,QLineEdit,QProgressBar
from PyQt5.QtGui import QImage, QPixmap, QFont, QLinearGradient, QColor, QBrush, QPainter
from PyQt5.QtCore import QTimer, Qt
from pyfirmata import Arduino
import sys
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
# Dictionary to track appliance states and timestamps

def find_com_port():
    if sys.platform.startswith('win'):
        for i in range(1, 256):
            port_name = f"COM{i}"
            try:
                with open(f"\\\\.\\{port_name}", "r+b") as port:
                    return port_name
            except OSError:
                pass  # Port not found or in use
    else:
        print("Unsupported operating system.")
        return None

    return None



appliance_states = {
    0: {"state": False, "last_toggle_time": time.time(), "on_duration": 0},  # Switch 1
    1: {"state": False, "last_toggle_time": time.time(), "on_duration": 0},  # Switch 2
    2: {"state": False, "last_toggle_time": time.time(), "on_duration": 0},  # Switch 3
    3: {"state": False, "last_toggle_time": time.time(), "on_duration": 0},  # Switch 4
}
# Initialize Arduino board

board = Arduino(f'{find_com_port()}')  # Update with your Arduino port
def calculate (n_fan , n_cooler , n_ac , n_light):
    avg_fan = 0.07
    avg_cooler = 0.20
    avg_ac = 1.2
    avg_light = 0.015

    res = (n_fan*avg_fan)+(n_cooler*avg_cooler)+(n_ac*avg_ac)+(n_light*avg_light)
    return res
print(calculate(12,0,4,8))
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

#to calculate power consumption
def calculate_ (n_fan , n_cooler , n_ac , n_light):
    avg_fan = 0.07
    avg_cooler = 0.20
    avg_ac = 1.2
    avg_light = 0.015
    res = (n_fan*avg_fan)+(n_cooler*avg_cooler)+(n_ac*avg_ac)+(n_light*avg_light)
    return res


# Default corner points (fallback if user doesn't set them)
DEFAULT_CORNER_POINTS = [(520, 108), (105, 214), (820, 255), (517, 591)]

# Global variables for statistics
total_people = 0
electricity_saved = 0
automatic_mode = True  # Start in Automatic Mode

class PowerConsumptionApp(QWidget):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Power Consumption Calculator")
        self.setGeometry(100, 100, 600, 400)

        layout = QGridLayout()

        self.appliance_labels = ["Fans", "Coolers", "ACs", "Light Bulbs"]
        self.entries = {}
        self.li = []

        for i, label in enumerate(self.appliance_labels):
            lbl = QLabel(label)
            entry = QLineEdit()
            entry.setPlaceholderText("Enter count")
            self.entries[label] = entry
            value = self.entries[label].text()
            self.li.append(value)


            layout.addWidget(lbl, i, 0)
            layout.addWidget(entry, i, 1)
            print(self.entries)
        self.calculate_button = QPushButton("Calculate Consumption")
        self.calculate_button.clicked.connect(self.calculate_consumption)
        layout.addWidget(self.calculate_button, len(self.appliance_labels), 0, 1, 2)

        self.result_label = QLabel(" Total Power consumptions.")
        layout.addWidget(self.result_label, len(self.appliance_labels) + 1, 0, 1, 2)



        self.next_button = QPushButton("Next")
        self.next_button.clicked.connect(self.next_)
        layout.addWidget(self.next_button, len(self.appliance_labels) + 2, 0, 1, 2)

        # Add Matplotlib FigureCanvas for chart display
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, len(self.appliance_labels) + 3, 0, 1, 2)

        self.setLayout(layout)
    def next_(self):
        global consumption_data
        consumption = self.consumption_data
        self.close()

        self.setup = SetupWindow(consumption)
        self.setup.show()
    def calculate_consumption(self):
        try:
            power_ratings = {"Fans": 60, "Coolers": 200, "ACs": 1500, "Light Bulbs": 10}
            total_power = 0
            self.consumption_data = []
            self.consumption_data_ = []
            labels = []

            print("Captured Inputs:")  # Debugging line

            for appliance, entry in self.entries.items():
                text_value = entry.text().strip()  # Remove unnecessary spaces
                print(f"{appliance}: '{text_value}'")  # Debugging line to print values

                if text_value.isdigit():  # Ensure only valid numbers are used
                    count = int(text_value)
                else:
                    count = 0  # If invalid input, set it to zero

                consumption_ = count * power_ratings[appliance]
                consumption = count
                total_power += consumption_

                if count >= 0:  # Only add non-zero values to the chart
                    self.consumption_data.append(consumption)
                    self.consumption_data_.append(consumption_)
                    labels.append(appliance)

            if not labels:  # If all inputs are empty or zero
                self.result_label.setText("Please enter valid appliance counts.")
            else:
                self.result_label.setText(f"Total Hourly Consumption: {total_power} Watts")
                self.update_chart(labels, self.consumption_data_)

        except Exception as e:
            self.result_label.setText(f"Error: {str(e)}")

    def update_chart(self, labels, data):
        self.ax.clear()
        self.ax.bar(labels, data, color=['blue', 'green', 'red', 'yellow'])
        self.ax.set_ylabel("Power Consumption (Watts)")
        self.ax.set_title("Appliance Power Usage")
        self.canvas.draw()

    def toggle_dark_mode(self):
        current_style = self.styleSheet()
        if "background-color" in current_style:
            self.setStyleSheet("")
        else:
            self.setStyleSheet("background-color: #333; color: white;")
            for entry in self.entries.values():
                entry.setStyleSheet("background-color: #555; color: white;")
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
    def __init__(self,consumption):
        super().__init__()
        self.setWindowTitle("Setup Corner Points")
        self.setGeometry(100, 100, 800, 600)
        self.consumption_data = consumption

        # rate of consumption
        self.cons_ = calculate(self.consumption_data[0], self.consumption_data[1], self.consumption_data[2],
                               self.consumption_data[3])

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
        self.instructions_label = QLabel("Automatically detecting corner points...", self)
        self.instructions_label.setStyleSheet("font-size: 16px; color: #333;")
        self.instructions_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.instructions_label)

        # Progress Bar (Loading Effect)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.layout.addWidget(self.progress_bar)

        # Proceed Button
        self.proceed_button = QPushButton("Proceed to Main Screen", self)
        self.proceed_button.setStyleSheet("""
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
        self.proceed_button.setEnabled(False)
        self.proceed_button.clicked.connect(self.redirect_to_main_window)
        self.layout.addWidget(self.proceed_button)

        # Timer for video feed updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_video_feed)
        self.timer.start(30)  # Update every 30ms

        # Variables for corner points
        self.corner_points = []
        self.is_processing = False

    def update_video_feed(self):
        success, image = cap.read()
        if not success:
            return

        if not self.is_processing:
            # Automatically detect corner points based on resolution
            frame_height, frame_width = image.shape[:2]
            self.corner_points = [
                (0, 0),  # Top-left
                (frame_width - 1, 0),  # Top-right
                (0, frame_height - 1),  # Bottom-left
                (frame_width - 1, frame_height - 1)  # Bottom-right
            ]
            self.is_processing = True

            # Simulate loading effect
            self.simulate_loading()

        # Draw corner points on the video feed
        for point in self.corner_points:
            cv2.circle(image, point, 10, (0, 255, 0), -1)

        # Convert image to PyQt-compatible format
        h, w, ch = image.shape
        bytes_per_line = ch * w
        qt_image = QImage(image.data, w, h, bytes_per_line, QImage.Format_BGR888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))

    def simulate_loading(self):
        # Simulate loading by incrementing the progress bar
        self.instructions_label.setText("Detecting corner points...")
        self.progress_value = 0
        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self.increment_progress)
        self.loading_timer.start(30)

    def increment_progress(self):
        if self.progress_value < 100:
            self.progress_value += 1
            self.progress_bar.setValue(self.progress_value)
        else:
            self.loading_timer.stop()
            self.instructions_label.setText("Corner points detected! Click 'Proceed to Main Screen'.")
            self.proceed_button.setEnabled(True)

    def redirect_to_main_window(self):
        global corner_points, cons_
        corner_points = self.corner_points
        cons_ = self.cons_
        self.close()

        self.main_window = MainWindow(corner_points, cons_)
        self.main_window.show()


class MainWindow(QMainWindow):
    def __init__(self, corner_points , cons_):
        super().__init__()

        self.setWindowTitle("Smart Room Monitoring")
        self.setGeometry(100, 100, 1200, 800)
        self.cons_ = cons_
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
        global appliance_states
        current_state = pins[switch_id].read()
        new_state = 1 if current_state == 0 else 0
        pins[switch_id].write(new_state)

        # Update appliance state and calculate ON duration
        now = time.time()
        if appliance_states[switch_id]["state"]:
            appliance_states[switch_id]["on_duration"] += now - appliance_states[switch_id]["last_toggle_time"]
        appliance_states[switch_id]["state"] = not appliance_states[switch_id]["state"]
        appliance_states[switch_id]["last_toggle_time"] = now

        self.switch_buttons[switch_id].setText(f"Switch {switch_id+1} ({'ON' if new_state else 'OFF'})")

    def update_video_feed(self):
        global total_people, electricity_saved, automatic_mode, appliance_states

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
                new_state = 0 if i in nearest_points else 1
                pins[i].write(new_state)

                # Update appliance state and calculate ON duration
                now = time.time()
                if appliance_states[i]["state"]:
                    appliance_states[i]["on_duration"] += now - appliance_states[i]["last_toggle_time"]
                appliance_states[i]["state"] = new_state == 0
                appliance_states[i]["last_toggle_time"] = now



        # Convert image to PyQt-compatible format
        h, w, ch = image.shape
        bytes_per_line = ch * w
        qt_image = QImage(image.data, w, h, bytes_per_line, QImage.Format_BGR888)
        self.video_label.setPixmap(QPixmap.fromImage(qt_image))

        # Update statistics labels
        total_on_hours = sum(state["on_duration"] / 3600 for state in appliance_states.values())
        # Calculate electricity saved (example logic)
        self.electricity_saved += total_on_hours * self.cons_  # Example: 0.1 kWh per person
        self.stats_label.setText(
            f"Total People: {self.total_people}\n"
            f"Electricity consumed: {round(self.electricity_saved, 2)} kWh\n"
            f"Total Appliances Active Time: {round(total_on_hours, 2)} hours"
        )


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = PowerConsumptionApp()
    window.show()
    sys.exit(app.exec_())

    # Release resources when the application closes
    cap.release()