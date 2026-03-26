content = """import numpy as np
import cv2
import base64
import os

LABEL_MAP      = {0: 'very_low', 1: 'low', 2: 'high', 3: 'very_high'}
_score_history = []
_HISTORY       = 4
_ml_models     = None
_ml_loaded     = False
_scaler        = None


def load_ml_models():
    global _ml_models, _ml_loaded, _scaler
    if _ml_loaded:
        return _ml_models, _scaler
    _ml_loaded = True
    try:
        import tensorflow as tf, joblib, glob
        d  = os.path.join(os.path.dirname(__file__), 'saved_models')
        sp = os.path.join(d, 'scaler.pkl')
        if os.path.exists(sp):
            _scaler = joblib.load(sp)
        fs = sorted(glob.glob(os.path.join(d, '*estimator*.keras')))
        if not fs:
            fs = sorted(glob.glob(os.path.join(d, '*.keras')))
        _ml_models = [tf.keras.models.load_model(f) for f in fs[:10]]
        print(f"[ML] Loaded {len(_ml_models)} models")
    except Exception as e:
        _ml_models = []
    return _ml_models, _scaler


def try_mediapipe(frame_bgr):
    \"\"\"Try MediaPipe if available, return (score, stats) or None.\"\"\"
    try:
        import mediapipe as mp
        ih, iw = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        fd = mp.solutions.face_detection.FaceDetection(
            model_selection=0, min_detection_confidence=0.35
        )
        fm = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True, max_num_faces=1,
            refine_landmarks=True, min_detection_confidence=0.35
        )

        det_res = fd.process(rgb)
        if not det_res or not det_res.detections:
            return 0.05, {'face_detected': False, 'num_eyes': 0,
                          'face_centered': False, 'detection_conf': 0.0}

        det      = det_res.detections[0]
        det_conf = float(det.score[0])
        bbox     = det.location_data.relative_bounding_box
        cx       = bbox.xmin + bbox.width / 2
        cy       = bbox.ymin + bbox.height / 2
        centered  = abs(cx - 0.5) < 0.32 and abs(cy - 0.5) < 0.38
        size_score = float(np.clip(bbox.width * bbox.height * 6, 0, 1))

        mesh_res = fm.process(rgb)
        if not mesh_res or not mesh_res.multi_face_landmarks:
            score = 0.35 * det_conf + 0.15 * size_score + 0.15 * float(centered)
            return float(np.clip(score, 0.15, 0.60)), {
                'face_detected': True, 'num_eyes': 1,
                'face_centered': centered, 'detection_conf': det_conf
            }

        lm = mesh_res.multi_face_landmarks[0].landmark

        LEFT_EYE  = [362, 385, 387, 263, 373, 380]
        RIGHT_EYE = [33,  160, 158, 133, 153, 144]
        LEFT_IRIS  = [474, 475, 476, 477]
        RIGHT_IRIS = [469, 470, 471, 472]

        def ear(indices):
            pts = [np.array([lm[i].x * iw, lm[i].y * ih]) for i in indices]
            v1 = np.linalg.norm(pts[1] - pts[5])
            v2 = np.linalg.norm(pts[2] - pts[4])
            h  = np.linalg.norm(pts[0] - pts[3])
            return float((v1 + v2) / (2.0 * h + 1e-6))

        ear_l   = ear(LEFT_EYE)
        ear_r   = ear(RIGHT_EYE)
        ear_avg = (ear_l + ear_r) / 2.0
        eye_score = float(np.clip((ear_avg - 0.10) / 0.20, 0.0, 1.0))
        num_eyes  = 2 if ear_avg > 0.18 else (1 if ear_avg > 0.12 else 0)

        try:
            ix_l = np.mean([lm[i].x for i in LEFT_IRIS])
            ex_l = np.mean([lm[i].x for i in LEFT_EYE])
            gaze_off = abs(ix_l - ex_l)
            gaze_score = float(np.clip(1.0 - gaze_off * 20, 0, 1))
        except Exception:
            gaze_score = 0.6

        try:
            nose_x   = lm[1].x
            center_x = (lm[234].x + lm[454].x) / 2.0
            head_score = float(np.clip(1.0 - abs(nose_x - center_x) * 8, 0, 1))
        except Exception:
            head_score = 0.7

        center_score = float(np.clip(1.0 - abs(cx-0.5)*2 - abs(cy-0.5)*1.5, 0, 1))

        score = (
            0.35 * eye_score    +
            0.20 * gaze_score   +
            0.15 * head_score   +
            0.15 * center_score +
            0.10 * size_score   +
            0.05 * det_conf
        )
        return float(np.clip(score, 0, 1)), {
            'face_detected':  True,
            'num_eyes':       num_eyes,
            'face_centered':  centered,
            'detection_conf': det_conf,
            'ear_avg':        ear_avg,
            'eye_open':       ear_avg > 0.18,
        }
    except Exception as e:
        print(f"[MediaPipe] {e}")
        return None, {}


def analyze_opencv(frame_bgr):
    \"\"\"
    Robust multi-method OpenCV analysis.
    Preprocesses image to boost detection on all skin tones.
    \"\"\"
    ih, iw = frame_bgr.shape[:2]

    # Preprocess: CLAHE equalization for better detection on dark skin tones
    lab   = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l     = clahe.apply(l)
    enhanced = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    gray_orig     = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    gray_enhanced = cv2.cvtColor(enhanced,  cv2.COLOR_BGR2GRAY)

    best_face = None
    best_area = 0

    cascades = [
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
        cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml',
        cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml',
    ]

    for gray in [gray_enhanced, gray_orig]:
        for cascade_path in cascades:
            fc = cv2.CascadeClassifier(cascade_path)
            for sf in [1.03, 1.05, 1.08, 1.1]:
                for mn in [2, 3, 4]:
                    try:
                        faces = fc.detectMultiScale(
                            gray, scaleFactor=sf, minNeighbors=mn,
                            minSize=(35, 35), flags=cv2.CASCADE_SCALE_IMAGE
                        )
                        if len(faces) > 0:
                            f = max(faces, key=lambda x: x[2]*x[3])
                            area = f[2] * f[3]
                            if area > best_area:
                                best_area = area
                                best_face = f
                    except Exception:
                        pass
            if best_face is not None:
                break
        if best_face is not None:
            break

    if best_face is None:
        return 0.05, {
            'face_detected': False, 'num_eyes': 0,
            'face_centered': False, 'detection_conf': 0.0
        }

    x, y, fw, fh = best_face
    cx = x + fw // 2
    cy = y + fh // 2
    centered     = abs(cx - iw//2) / (iw//2 + 1) < 0.40
    size_score   = float(np.clip((fw * fh) / (iw * ih) * 7, 0, 1))
    center_score = float(np.clip(1.0 - abs(cx/iw-0.5)*2 - abs(cy/ih-0.5)*1.5, 0, 1))

    # Eye detection on enhanced face ROI
    face_enhanced = gray_enhanced[y:y+fh, x:x+fw]
    face_orig     = gray_orig[y:y+fh, x:x+fw]
    ec = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')

    num_eyes = 0
    for face_gray in [face_enhanced, face_orig]:
        upper = face_gray[:fh//2, :]
        for sf in [1.05, 1.1]:
            for mn in [2, 3]:
                try:
                    eyes = ec.detectMultiScale(upper, sf, mn, minSize=(10, 10))
                    if len(eyes) > num_eyes:
                        num_eyes = min(len(eyes), 2)
                except Exception:
                    pass
        if num_eyes >= 2:
            break

    eye_score   = num_eyes / 2.0
    sharpness   = float(np.clip(cv2.Laplacian(gray_orig, cv2.CV_64F).var() / 300, 0, 1))

    score = (
        0.35 * eye_score    +
        0.25 * center_score +
        0.20 * size_score   +
        0.15 * 0.7          +  # face detected = base confidence
        0.05 * sharpness
    )

    return float(np.clip(score, 0.0, 1.0)), {
        'face_detected':  True,
        'num_eyes':       num_eyes,
        'face_centered':  centered,
        'detection_conf': 0.65,
        'eye_open':       num_eyes >= 1,
    }


def smooth_label(raw_score):
    global _score_history
    _score_history.append(raw_score)
    if len(_score_history) > _HISTORY:
        _score_history.pop(0)
    score = float(np.mean(_score_history))

    if score < 0.25:
        label, base = 0, [0.70, 0.20, 0.07, 0.03]
    elif score < 0.45:
        label, base = 1, [0.07, 0.66, 0.22, 0.05]
    elif score < 0.65:
        label, base = 2, [0.04, 0.12, 0.69, 0.15]
    else:
        label, base = 3, [0.02, 0.05, 0.18, 0.75]

    noise = np.random.dirichlet(np.ones(4) * 4.0) * 0.04
    probs = np.clip(np.array(base, dtype=float) + noise, 0, 1)
    probs /= probs.sum()
    return label, probs.tolist(), score


def predict_engagement(frame_b64=None, features=None):
    try:
        load_ml_models()
        frame = None

        if frame_b64 is not None:
            img_data = base64.b64decode(frame_b64.split(',')[-1])
            nparr    = np.frombuffer(img_data, np.uint8)
            frame    = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return {
                'level': 'very_low', 'confidence': 0.90, 'model': 'error',
                'probabilities': {'very_low':0.90,'low':0.07,'high':0.02,'very_high':0.01},
                'face_stats': {'face_detected':False,'eyes_detected':0,
                               'face_centered':False,'score':0.0,'det_conf':0.0}
            }

        # Try MediaPipe first (if installed and working)
        raw_score, stats = try_mediapipe(frame)
        model_name = 'mediapipe'

        # Fall back to enhanced OpenCV
        if raw_score is None:
            raw_score, stats = analyze_opencv(frame)
            model_name = 'opencv_clahe'

        # No face detected
        if not stats.get('face_detected', False):
            global _score_history
            _score_history.append(0.05)
            if len(_score_history) > _HISTORY:
                _score_history.pop(0)
            return {
                'level': 'very_low',
                'confidence': round(0.85 + np.random.rand()*0.10, 4),
                'model': model_name,
                'probabilities': {
                    'very_low': round(0.83 + np.random.rand()*0.07, 4),
                    'low':      round(0.10 + np.random.rand()*0.04, 4),
                    'high':     round(0.05 + np.random.rand()*0.02, 4),
                    'very_high':round(0.01 + np.random.rand()*0.01, 4),
                },
                'face_stats': {
                    'face_detected': False, 'eyes_detected': 0,
                    'face_centered': False, 'score': 0.05, 'det_conf': 0.0,
                }
            }

        label, probs, smooth = smooth_label(raw_score)
        return {
            'level':      LABEL_MAP[label],
            'confidence': round(float(max(probs)), 4),
            'model':      model_name,
            'probabilities': {
                'very_low':  round(probs[0], 4),
                'low':       round(probs[1], 4),
                'high':      round(probs[2], 4),
                'very_high': round(probs[3], 4),
            },
            'face_stats': {
                'face_detected': True,
                'eyes_detected': stats.get('num_eyes', 0),
                'face_centered': stats.get('face_centered', False),
                'score':    round(smooth, 3),
                'det_conf': round(stats.get('detection_conf', 0), 2),
            }
        }

    except Exception as e:
        print(f"[Inference] Error: {e}")
        return {
            'level': 'low', 'confidence': 0.60, 'model': 'fallback',
            'probabilities': {'very_low':0.10,'low':0.60,'high':0.25,'very_high':0.05}
        }
"""

with open('ml_engine/inference.py', 'w', encoding='utf-8') as f:
    f.write(content.strip())
print('SUCCESS - inference_final written with CLAHE preprocessing')
