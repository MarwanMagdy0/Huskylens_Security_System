from huskylib import HuskyLensLibrary
from playsound import playsound
from picamera2 import Picamera2
from datetime import datetime
from collections import deque
from threading import Thread
from gpiozero import Buzzer
from gpiozero import Servo
import smbus2 as smbus
import serial
import time
import cv2
import os
os.makedirs("/home/pi/videos", exist_ok=True)
face_id2zone = {1 : 1, 2 : 2} # {face_id : zone}
buzzer = Buzzer(17)

detector = cv2.QRCodeDetector()
cam = Picamera2()
cam.configure(cam.create_preview_configuration(main={"format": 'RGB888', "size": (640, 480)}))
cam.start()

NUMBER_OF_CONSECUTIVE_FACE_ID = 20 # this is the number of consecutive faces in the queue on which if the consecutive ids exceeds this number there is an action that will be taken
TIME_FOR_UNKNOWN_FACE = 20 # this is the time in seconds that is given to the unknown face to show QrCode
ALARM_SECONDS = 5 # set alarm for 5 seconds

SEGMENT_DURATION = 30 # duration of saving videos in seconds
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
            frame = CameraSaver.camera_frame
            qr_data = get_qr_code_data(frame)
            if qr_data == "f851256dff2a8825ad4af615111b6a4f":
                print("[Security Check] person identified", flush=True)
                threaded_sound_play(["/home/pi/HUSKYLENS/person_identified.mp3"])
                buzzer.off()
                break
        else:
            print("[Security Alarm] unrecognized person", flush=True)
            threaded_sound_play(["/home/pi/HUSKYLENS/You_are_not_in_the_database.mp3"])
            buzzer.off()
            SecurityMethods.alarm_for_n_seconds(ALARM_SECONDS)

    @staticmethod
    def check_this_face_is_in_its_zone(face_id):
        if face_id2zone[face_id] != SecurityMethods.zone:
            print("please go to your zone", flush=True)
            threaded_sound_play(["/home/pi/HUSKYLENS/please_go_to_your_zone.mp3"])
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
        t = Thread(target=ZoneHandeler.zone_serial_thread_loop)
        t.start()

    @staticmethod
    def zone_serial_thread_loop():
        moving_sign = True
        try:
            ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
            ser.flush()
        except:
            print("Error: Could not open serial port", flush=True)
            return

        while True:
            time.sleep(0.1)
            try:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8').rstrip()
                    print("Serial Recv:", line, flush=True)
                    if line == "Zone Changed":
                        if SecurityMethods.zone == 3:
                            moving_sign = -1
                        elif SecurityMethods.zone == 1:
                            moving_sign = 1
                        SecurityMethods.zone += 1 * moving_sign
            except:
                print("Error: Problem with serial data", flush=True)

def threaded_sound_play(audio_file_paths : list):
    # Play the sound
    def playsound_thread(audio_file_paths: list):
        for audio_file_path in audio_file_paths:
            playsound(audio_file_path)
    
    t = Thread(target=playsound_thread, args=(audio_file_paths, ))
    t.start()


class CameraSaver:
    camera_frame = cam.capture_array()
    def __init__(self):
        t = Thread(target=self.loop)
        t.start()

    def loop(self):
        filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out = cv2.VideoWriter(f'/home/pi/videos/{filename}.avi', cv2.VideoWriter_fourcc(*'DIVX'), 20.0, (640, 480))
        start_time = time.time()
        while True:
            cv2.waitKey(1)
            CameraSaver.camera_frame = cam.capture_array()
            if CameraSaver.camera_frame is not None:
                out.write(cv2.resize(CameraSaver.camera_frame, (640,480)))
            else:
                print("[Rpi Frame is None]")
            if time.time() - start_time >= SEGMENT_DURATION:
                print("[Video Released]####################################")
                time.sleep(0.3)
                out.release()
                time.sleep(0.3)
                filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                out = cv2.VideoWriter(f'/home/pi/videos/{filename}.avi', cv2.VideoWriter_fourcc(*'DIVX'), 20.0, (640,480))
                start_time = time.time()
