import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

from gpiozero import LED, Buzzer, Button, OutputDevice
from signal import pause

from detect import main

cred = credentials.Certificate("dbkey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://smart-door-lock-58-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

target_id = "-NirdTJoPlvLn407NKev"

data_ref = db.reference('lock/' + target_id)

led_pin = 27 
buzzer_pin = 17 
button_pin = 22 
relay_pin = 23 

led = LED(led_pin)
buzzer = Buzzer(buzzer_pin)
button = Button(button_pin)
relay = OutputDevice(relay_pin, active_high=True, initial_value=False)

def button_pressed():
    led.toggle() 
    if led.is_lit:
        buzzer.on()  
        relay.on()
        print("ON")
    else:
        buzzer.off()  
        relay.off()
        print("OFF")

def on_data_change(event):
    #print(f'Data for ID {target_id} updated:', event.data)
    data_value = event.data
    #print(data_value.get("led"))
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

button.when_pressed = button_pressed

data_ref.listen(on_data_change)

main()

pause()
