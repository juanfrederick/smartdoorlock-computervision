import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

from gpiozero import LED, Buzzer, Button, OutputDevice
from signal import pause
import time
import threading

from detect import main
from testKey import keypad

cred = credentials.Certificate("dbkey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://smart-door-lock-58-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

target_id = "-NirdTJoPlvLn407NKev"

data_ref = db.reference('lock/' + target_id)

led_pin = 27
buzzer_pin = 17
button_pin = 22
relay_pin = 21

led = LED(led_pin)
buzzer = Buzzer(buzzer_pin)
button = Button(button_pin)
relay = OutputDevice(relay_pin, active_high=True, initial_value=False)

def button_pressed():
    led.on()
    buzzer.on()
    relay.on()
    print("ON")
    time.sleep(1.5)
    buzzer.off()
    relay.off()
    led.off()
    print("OFF")

def on_data_change(event):
    data_value = event.data
    if data_value.get("led") and data_value.get("buzzer") and data_value.get("relay"):
        print("ON")
        buzzer.on()
        relay.on()
        led.on()
    else:
        print("OFF")
        buzzer.off()
        relay.off()
        led.off()

# Main loop for keypad
def keypadFunc():
    password = "1234"
    num = ""
    try:
        while True:
            key = keypad()
            if key:
                print("Pressed:", key)
                num = num + key
                print("num:", num)
                
                buzzer.on()
                time.sleep(0.2)
                buzzer.off()
                
                if(len(num) == 4):
                    if(num == password):
                        relay.on()
                        led.on()
                        print("buzzer ring twice open relay")
                        time.sleep(0.2)
                        buzzer.on()
                        time.sleep(0.2)
                        buzzer.off()
                        time.sleep(0.2)
                        buzzer.on()
                        time.sleep(0.2)
                        buzzer.off()
                        time.sleep(1)
                        relay.off()
                        led.off()
                    else:
                        print("buzzer ring long")
                        time.sleep(0.2)
                        buzzer.on()
                        time.sleep(1)
                        buzzer.off()
                    
                    num = ""

            time.sleep(0.2)
    except KeyboardInterrupt:
        GPIO.cleanup() 

button.when_pressed = button_pressed

data_ref.listen(on_data_change)

thread1 = threading.Thread(target=main)
thread1.start()

thread2 = threading.Thread(target=keypadFunc)
thread2.start()

pause()
