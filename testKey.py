import RPi.GPIO as GPIO
import time
from gpiozero import LED, Buzzer, OutputDevice

ROWS = [20, 16, 12, 5]
COLS = [26, 19, 13, 6]

keys = [
    ['1', '2', '3', 'a'],
    ['4', '5', '6', 'b'],
    ['7', '8', '9', 'c'],
    ['*', '0', '#', 'd']
]

# Set up GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(ROWS, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(COLS, GPIO.OUT)

# Function to read the keypad
def keypad():
    for col_num, col_pin in enumerate(COLS):
        GPIO.output(col_pin, 0)
        for row_num, row_pin in enumerate(ROWS):
            if GPIO.input(row_pin) == 0:
                return keys[row_num][col_num]
        GPIO.output(col_pin, 1)