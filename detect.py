import argparse
import sys
import time

import cv2
import mediapipe as mp
import numpy as np
import base64

from datetime import datetime

from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from utils import visualize

from sendNotif import loop_send_message

import firebase_admin
from firebase_admin import credentials, db

# cred = credentials.Certificate("dbkey.json")
# firebase_admin.initialize_app(cred, {
#     'databaseURL': 'https://smart-door-lock-58-default-rtdb.asia-southeast1.firebasedatabase.app/'
# })

def run(model: str, camera_id: int, width: int, height: int, category_allowlist: list) -> None:
  """Continuously run inference on images acquired from the camera.

  Args:
    model: Name of the TFLite object detection model.
    camera_id: The camera id to be passed to OpenCV.
    width: The width of the frame captured from the camera.
    height: The height of the frame captured from the camera.
  """
  ref = db.reference('/detectHistory')

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
    current_frame_copy = cv2.cvtColor(mp_image.numpy_view(), cv2.COLOR_RGB2BGR)

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

            if(notif_counter == 30):
                print("===============SEND NOTIFICATION=============== There's ", max_detected, " person coming")

                current_time = datetime.utcnow().isoformat()
                array_of_crop = []

                image_for_crop = np.copy(current_frame)
                image_for_full = np.copy(current_frame_copy)

                full_image = image_for_full

                full_width = int(full_image.shape[1] * 30 / 100)
                full_height = int(full_image.shape[0] * 30 / 100)

                full_resized = cv2.resize(full_image, (full_width, full_height))
                
                full_bytes = cv2.imencode('.jpg', full_resized)[1].tobytes()
                full_encoded = base64.b64encode(full_bytes).decode('utf-8')

                for obj in detections:
                    x = obj.bounding_box.origin_x
                    y = obj.bounding_box.origin_y
                    w = obj.bounding_box.width
                    h = obj.bounding_box.height
                    single_crop = image_for_crop[y:y+h, x:x+w]

                    crop_width = int(single_crop.shape[1] * 30 / 100)
                    crop_height = int(single_crop.shape[0] * 30 / 100)

                    resized_image = cv2.resize(single_crop, (crop_width, crop_height))

                    image_bytes = cv2.imencode('.jpg', resized_image)[1].tobytes()
                    encoded_image = base64.b64encode(image_bytes).decode('utf-8')

                    array_of_crop.append(encoded_image)

                data = {"date": current_time, "fullImage": full_encoded, "cropImage": array_of_crop, "lockId": "-NirdTJoPlvLn407NKev"}

                new_data_ref = ref.push(data) 
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
      default=320)
  parser.add_argument(
      '--frameHeight',
      help='Height of frame to capture from camera.',
      required=False,
      type=int,
      default=240)
  parser.add_argument(
      '--categoryAllowList',
      help='Comma-separated list of categories to allow (e.g., person,car).',
      required=False,
      default=['person'])
  args = parser.parse_args()

  run(args.model, int(args.cameraId), args.frameWidth, args.frameHeight, args.categoryAllowList)


if __name__ == '__main__':
  main()