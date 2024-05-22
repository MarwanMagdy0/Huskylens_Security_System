from huskylib import HuskyLensLibrary
from picamera2 import Picamera2
from collections import deque
from threading import Thread
from gpiozero import Buzzer
from gpiozero import Servo
import smbus2 as smbus
import time
import cv2
import os

face_id2zone = {1 : 1, 2 : 2} # {face_id : zone}
buzzer = Buzzer(17)

detector = cv2.QRCodeDetector()
cam = Picamera2()
cam.configure(cam.create_preview_configuration(main={"format": 'RGB888', "size": (640, 480)}))
cam.start()

NUMBER_OF_CONSECUTIVE_FACE_ID = 50 # this is the number of consecutive faces in the queue on which if the consecutive ids exceeds this number there is an action that will be taken
TIME_FOR_UNKNOWN_FACE = 20 # this is the time in seconds that is given to the unknown face to show QrCode
ALARM_SECONDS = 5 # set alarm for 5 seconds


arduino_address = 0x08
sda_pin = 8
scl_pin = 9

servo_pin = 18
servo = Servo(servo_pin)
SERVO_STEP = 0.01
def get_qr_code_data(frame):
    data, vertices_array, binary_qrcode = detector.detectAndDecode(frame)
    if vertices_array is not None and str(data) != "":
        return str(data)


class FixedSizeQueue:
    def __init__(self, max_size):
        self.queue = deque(maxlen=max_size)

    def add(self, item):
        self.queue.append(item)

    def max_repeated(self):
        if not self.queue:
            return None, 0

        max_item = None
        max_count = 0
        current_item = None
        current_count = 0

        for item in self.queue:
            if item == current_item:
                current_count += 1
            else:
                current_item = item
                current_count = 1

            if current_count > max_count:
                max_item = current_item
                max_count = current_count

        return max_item, max_count

    def pop_first(self):
        if self.queue:
            return self.queue.popleft()

    def empty(self):
        self.queue.clear()

    def __repr__(self):
        return f"FixedSizeQueue({list(self.queue)})"

class SecurityMethods:
    zone = 1

    @staticmethod
    def this_face_is_not_in_data_set():
        """
        This methods makes robot wait for this unknown person to pass the qrcode infront of rpi-camera
        if user dont provid the qrcode in {TIME_FOR_UNKNOWN_FACE} seconds robot will set alaram for {ALARM_SECONDS}
        """
        start_time = time.time()
        buzzer.beep(0.5, 0.5)
        while time.time() - start_time < TIME_FOR_UNKNOWN_FACE:
            frame = cam.capture_array()
            qr_data = get_qr_code_data(frame)
            if qr_data == "f851256dff2a8825ad4af615111b6a4f":
                print("[Security Check] person identified", flush=True)
                buzzer.off()
                break
        else:
            print("[Security Alarm] unrecognized person", flush=True)
            buzzer.off()
            SecurityMethods.alarm_for_n_seconds(ALARM_SECONDS)

    @staticmethod
    def check_this_face_is_in_its_zone(face_id):
        if face_id2zone[face_id] != SecurityMethods.zone:
            print("please go to your zone", flush=True)
            SecurityMethods.alarm_for_n_seconds(2, 1, 0.5)

    @staticmethod
    def alarm_for_n_seconds(n_seconds, on_time=0.1, off_time=0.1):
        start_time = time.time()
        while time.time() - start_time < n_seconds:
            buzzer.on()
            time.sleep(on_time)
            buzzer.off()
            time.sleep(off_time)
        buzzer.off()


class ZoneHandeler:
    def __init__(self):
        t = Thread(target=ZoneHandeler.zone_i2c_thread_loop)
        t.start()

    @staticmethod
    def zone_i2c_thread_loop():
        bus = smbus.SMBus(1)
        while True:
            time.sleep(0.1)
            try:
                data = bus.read_byte(arduino_address)
                print("I2C Recv:", data, flush=True)
                SecurityMethods.zone = int(data)
            except:
                print("Error: Arduino not detected or data problem", flush=True)
