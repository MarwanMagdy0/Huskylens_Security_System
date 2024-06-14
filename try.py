from utiles import *
import subprocess

def is_device_present(bus, address):
    try:
        # Write a dummy byte to see if the device acknowledges
        bus.write_byte(address, 0)
        return True
    except OSError:
        return False

# Run the command and capture the output
address = 0x32
bus_number = 1

with smbus.SMBus(bus_number) as bus:
    while not is_device_present(bus, address):
        print("Device 32 not found.")
        buzzer.on()
        time.sleep(0.5)
        buzzer.off()
        time.sleep(1)

hl= HuskyLensLibrary("I2C","",address=0x32)
hl.algorthim("ALGORITHM_FACE_RECOGNITION")
#hl.forget()
#hl.setCustomName("ronaldo", 2)
for i in [0.5,0.3,0.1]:
    buzzer.on()
    time.sleep(i)
    buzzer.off()
    time.sleep(0.1)
buzzer.off()

class MainProgram:
    def __init__(self):
        self.queue = FixedSizeQueue(100)
        self.servo_value = -1
        self.servo_sign = 1

    def run(self):
        while True:
            time.sleep(1/30) # lock the loop at 30fps
            blocks = hl.blocks()

            for block in blocks:
                if len(block) == 5:
                    self.queue.add(block[4])

            if len(blocks) == 0:
                self.queue.pop_first()

            self.handle_faces()
            self.handle_servo()

    def handle_servo(self):
        self.servo_value += SERVO_STEP * self.servo_sign
        if self.servo_value >=1:
            self.servo_sign =-1
            self.servo_value = 1
        elif self.servo_value <=-1:
            self.servo_sign = 1
            self.servo_value = -1
        servo.value = self.servo_value
        print(f"Servo Value: {round(self.servo_value, 2)}", flush=True)


    def handle_faces(self):
        """This method handle the faces seen by the huskylens camera
        """
        # print(self.queue.max_repeated(), self.queue, blocks)
        max_repeated_id, n_times = self.queue.max_repeated()
        if n_times > NUMBER_OF_CONSECUTIVE_FACE_ID and max_repeated_id is not None:
            #print("face_id", max_repeated_id, "repeated:", n_times)
            print(self.queue, flush=True)
            if max_repeated_id == 0:
                SecurityMethods.this_face_is_not_in_data_set()
            else:
                SecurityMethods.check_this_face_is_in_its_zone(max_repeated_id)
            self.queue.empty()

if __name__ == "__main__":
    ZoneHandeler()
    CameraSaver()
    main_programe = MainProgram()
    main_programe.run()
