import numpy as np
print('NumPy:', np.__version__)

import tensorflow as tf
print('TF:', tf.__version__)

import mediapipe as mp
print('MediaPipe:', mp.__version__)

fd = mp.solutions.face_detection.FaceDetection()
print('ALL OK - solutions API works')
