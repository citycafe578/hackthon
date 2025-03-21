import sounddevice as sd
import numpy as np
import sys
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QPushButton, 
                            QLabel, QSlider, QComboBox)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
import random
import threading
import time
from pydub import AudioSegment
import pyaudio

def time_worker():
    while True:
        time.sleep(5)  # 每 5 秒執行一次
        timemode = random.randint(0, 1)
        gain = 10 if timemode == 1 else 0
        print(f"隨機更新 Gain: {gain}")
        # 如果需要更新 GUI，請使用信號或其他方式與主執行緒通信

# 啟動執行緒
time_thread = threading.Thread(target=time_worker, daemon=True)
time_thread.start()

class WorkerThread(QThread):
    update_signal = pyqtSignal(str)

    def run(self):
        # 在這裡執行非 GUI 的邏輯
        import time
        for i in range(5):
            self.update_signal.emit(f"更新訊息 {i}")
            time.sleep(1)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.gain = 5.0
        self.stream = None
        self.devices = self.get_devices()  # 改為獲取所有裝置
        self.initUI()

        # 啟動 QTimer，每 5 秒更新一次 gain
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_gain_randomly)
        self.timer.start(2500)  # 每 5000 毫秒（5 秒）觸發一次

        # 啟動執行緒
        self.thread = WorkerThread()
        self.thread.update_signal.connect(self.update_label)
        self.thread.start()

    def get_devices(self):
        input_devices = []
        output_devices = []
        # 新增預設裝置
        try:
            default_input = sd.default.device[0]
            default_output = sd.default.device[1]
            input_devices.append((-1, "系統預設輸入", 'input'))
            output_devices.append((-1, "系統預設輸出", 'output'))
        except Exception as e:
            print(f"無法取得預設裝置: {e}")

        for i, dev in enumerate(sd.query_devices()):
            try:
                if dev['max_input_channels'] > 0:
                    input_devices.append((i, f"{dev['name']} (ID: {i})", 'input'))
                if dev['max_output_channels'] > 0:
                    output_devices.append((i, f"{dev['name']} (ID: {i})", 'output'))
            except Exception as e:
                print(f"跳過裝置 {i}: {e}")
        return input_devices, output_devices

    def initUI(self):
        self.setWindowTitle("Audio Processor")
        self.setGeometry(100, 100, 400, 200)

        layout = QVBoxLayout()

        # 修改裝置選擇介面
        self.input_label = QLabel("輸入裝置:")
        layout.addWidget(self.input_label)

        self.input_combo = QComboBox()
        input_devices, _ = self.devices
        for dev_id, dev_name, _ in input_devices:
            self.input_combo.addItem(f"{dev_name}", dev_id)
        layout.addWidget(self.input_combo)

        self.output_label = QLabel("輸出裝置:")
        layout.addWidget(self.output_label)

        self.output_combo = QComboBox()
        _, output_devices = self.devices
        for dev_id, dev_name, _ in output_devices:
            self.output_combo.addItem(f"{dev_name}", dev_id)
        layout.addWidget(self.output_combo)

        self.label = QLabel(f"Gain: {self.gain}")
        layout.addWidget(self.label)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setValue(int(self.gain * 10))  # Convert gain value to slider value
        self.slider.valueChanged.connect(self.update_gain)
        layout.addWidget(self.slider)

        self.start_button = QPushButton("Start", self)
        self.start_button.clicked.connect(self.start_audio)
        layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop", self)
        self.stop_button.clicked.connect(self.stop_audio)
        self.stop_button.setEnabled(False)  # Initially disable stop button
        layout.addWidget(self.stop_button)

        self.setLayout(layout)

    def update_gain(self):
        # self.gain = self.slider.value() / 10.0
        self.gain = self.time_setting()
        self.label.setText(f"Gain: {self.gain}")

    def update_gain_randomly(self):
        self.gain = self.time_setting()
        self.label.setText(f"Gain: {self.gain}")

    def update_label(self, text):
        self.label.setText(text)

    def audio_callback(self, indata, outdata, frames, time, status):
        if status:
            print(status)
        try:
            processed_data = indata * self.gain
            outdata[:] = processed_data
        except Exception as e:
            print(f"音訊處理錯誤: {e}")
            outdata.fill(0)
        
    def start_audio(self):
        try:
            input_device = self.input_combo.currentData()
            output_device = self.output_combo.currentData()
            
            if input_device == -1:
                input_device = sd.default.device[0]
            if output_device == -1:
                output_device = sd.default.device[1]


            try:
                input_info = sd.query_devices(input_device)
                output_info = sd.query_devices(output_device)
            except Exception as e:
                print(f"無法查詢裝置資訊: {e}")
                return

            blocksize = 512
            
            self.stream = sd.Stream(
                device=(input_device, output_device),
                samplerate=4000,
                channels=(1, 1),
                callback=self.audio_callback,
                dtype=np.float32,
                blocksize=blocksize
            )
            self.stream.start()
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            print(f"已啟動音訊串流 (輸入: {input_device}, 輸出: {output_device})")
        except Exception as e:
            print(f"啟動串流時發生錯誤: {type(e).__name__} - {str(e)}")
            self.stop_audio()

    def stop_audio(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            print("Audio stream stopped")

    def closeEvent(self, event):
        self.stop_audio()
        self.save_settings()
        event.accept()

    def time_setting(self):
        timemode = random.randint(0, 1)
        return 10 if timemode == 1 else 0

class BadMicThread(QThread):
    def __init__(self):
        super().__init__()
        self.app = None
        self.window = None

    def run(self):
        # 啟動 PyQt 的事件迴圈
        self.app = QApplication.instance() or QApplication([])
        self.window = MainWindow()
        self.window.show()
        self.app.exec()

def bad_mic_start():
    thread = BadMicThread()
    thread.start()
    return thread

def start_function(self, name, func):
    if name not in self.running or not self.running[name]:
        if name == "bad_mic":
            # 啟動 bad_mic 的 GUI 執行緒
            thread = func()
            self.threads[name] = thread
            self.running[name] = True
        else:
            # 其他功能可以放入執行緒中運行
            thread = threading.Thread(target=func, daemon=True)
            self.threads[name] = thread
            self.running[name] = True
            thread.start()
        print(f"{name} 已啟動")
    else:
        print(f"{name} 已在運行中")
