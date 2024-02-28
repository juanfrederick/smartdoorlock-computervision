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

led_pin = 27  # Ganti dengan nomor pin yang sesuai
buzzer_pin = 17  # Ganti dengan nomor pin yang sesuai
button_pin = 22  # Ganti dengan nomor pin yang sesuai
relay_pin = 23  # Ganti dengan nomor pin yang sesuai

led = LED(led_pin)
buzzer = Buzzer(buzzer_pin)
button = Button(button_pin)
relay = OutputDevice(relay_pin, active_high=True, initial_value=False)

def button_pressed():
    led.toggle()  # Mengubah status LED (hidup/mati)
    if led.is_lit:
        buzzer.on()  # Hidupkan buzzer jika LED menyala
        relay.on()
        print("ON")
    else:
        buzzer.off()  # Matikan buzzer jika LED mati
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

# Menghubungkan fungsi button_pressed() dengan peristiwa saat tombol ditekan
button.when_pressed = button_pressed

# Menetapkan fungsi sebagai pendengar perubahan data
data_ref.listen(on_data_change)

main()

# Jaga program tetap berjalan
pause()
