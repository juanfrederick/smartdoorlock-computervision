import argparse
import sys
import time

import cv2
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from utils import visualize

from sendNotif import loop_send_message

from gpiozero import LED, Buzzer, Button, OutputDevice
from signal import pause

def run_lock():
    cred = credentials.Certificate("key.json")
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

    # Jaga program tetap berjalan
    pause()

def run(model: str, camera_id: int, width: int, height: int, category_allowlist: list) -> None:
  """Continuously run inference on images acquired from the camera.

  Args:
    model: Name of the TFLite object detection model.
    camera_id: The camera id to be passed to OpenCV.
    width: The width of the frame captured from the camera.
    height: The height of the frame captured from the camera.
  """

  # Variables to calculate FPS
  counter, fps = 0, 0
  start_time = time.time()

  # Start capturing video input from the camera
  cap = cv2.VideoCapture(camera_id)
  cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
  cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

  # Visualization parameters
  row_size = 20  # pixels
  left_margin = 24  # pixels
  text_color = (0, 0, 255)  # red
  font_size = 1
  font_thickness = 1
  fps_avg_frame_count = 10

  detection_result_list = []

  def visualize_callback(result: vision.ObjectDetectorResult,
                         output_image: mp.Image, timestamp_ms: int):
      result.timestamp_ms = timestamp_ms
      detection_result_list.append(result)


  # Initialize the object detection model
  base_options = python.BaseOptions(model_asset_path=model)
  options = vision.ObjectDetectorOptions(base_options=base_options,
                                         running_mode=vision.RunningMode.LIVE_STREAM,
                                         max_results=5,
                                         score_threshold=0.5,
                                         result_callback=visualize_callback,
                                         category_allowlist=category_allowlist)
  detector = vision.ObjectDetector.create_from_options(options)


  notif_counter = 0
  max_detected = 0

  # Continuously capture images from the camera and run inference
  while cap.isOpened():
    success, image = cap.read()
    if not success:
      sys.exit(
          'ERROR: Unable to read from webcam. Please verify your webcam settings.'
      )

    counter += 1
    image = cv2.flip(image, 1)

    # Convert the image from BGR to RGB as required by the TFLite model.
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)

    # Run object detection using the model.
    detector.detect_async(mp_image, counter)
    current_frame = mp_image.numpy_view()
    current_frame = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR)

    # Calculate the FPS
    if counter % fps_avg_frame_count == 0:
        end_time = time.time()
        fps = fps_avg_frame_count / (end_time - start_time)
        start_time = time.time()

    # Show the FPS
    fps_text = 'FPS = {:.1f}'.format(fps)
    text_location = (left_margin, row_size)
    cv2.putText(current_frame, fps_text, text_location, cv2.FONT_HERSHEY_PLAIN,
                font_size, text_color, font_thickness)

    if detection_result_list:
        detections = detection_result_list[0].detections
        num_detections = len(detections)

        if detections:

            if (max_detected < num_detections):
                print("MASUK")
                max_detected = num_detections

            notif_counter += 1
            print(num_detections, " detected. max human detected = ", max_detected, ". notif counter = ", notif_counter)

            if(notif_counter == 300):
                print("===============SEND NOTIFICATION=============== There's ", max_detected, " person coming")
                loop_send_message("Smart Door Lock", f"There's {max_detected} person coming")
            
            if(notif_counter > sys.maxsize):
                notif_counter = 0
            
        else:
            notif_counter = 0
            max_detected = 0
            print("not")

        # print(detection_result_list[0].detections)
        vis_image = visualize(current_frame, detection_result_list[0])
        cv2.imshow('object_detector', vis_image)
        detection_result_list.clear()
    else:
        cv2.imshow('object_detector', current_frame)

    # Stop the program if the ESC key is pressed.
    if cv2.waitKey(1) == 27:
      break

  detector.close()
  cap.release()
  cv2.destroyAllWindows()

def main():
  parser = argparse.ArgumentParser(
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  parser.add_argument(
      '--model',
      help='Path of the object detection model.',
      required=False,
      default='efficientdet_lite0.tflite')
  parser.add_argument(
      '--cameraId', help='Id of camera.', required=False, type=int, default=0)
  parser.add_argument(
      '--frameWidth',
      help='Width of frame to capture from camera.',
      required=False,
      type=int,
      default=1280)
  parser.add_argument(
      '--frameHeight',
      help='Height of frame to capture from camera.',
      required=False,
      type=int,
      default=720)
  parser.add_argument(
      '--categoryAllowList',
      help='Comma-separated list of categories to allow (e.g., person,car).',
      required=False,
      default=['person'])
  args = parser.parse_args()

  run(args.model, int(args.cameraId), args.frameWidth, args.frameHeight, args.categoryAllowList)
  run_lock()

if __name__ == '__main__':
  main()