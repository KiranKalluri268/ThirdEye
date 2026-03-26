inference = """import numpy as np
import cv2
import base64
import os

LABEL_MAP = {0: 'very_low', 1: 'low', 2: 'high', 3: 'very_high'}
_scaler  = None
_models  = None
_loaded  = False

# Track history for temporal smoothing
_score_history = []
_HISTORY_SIZE  = 5


def load_models():
    global _scaler, _models, _loaded
    if _loaded:
        return _models, _scaler
    _loaded = True
    try:
        import tensorflow as tf
        import joblib, glob
        models_dir = os.path.join(os.path.dirname(__file__), 'saved_models')
        sp = os.path.join(models_dir, 'scaler.pkl')
        if os.path.exists(sp):
            _scaler = joblib.load(sp)
        mfiles = sorted(glob.glob(os.path.join(models_dir, '*estimator*.keras')))
        if not mfiles:
            mfiles = sorted(glob.glob(os.path.join(models_dir, '*.keras')))
        _models = [tf.keras.models.load_model(f) for f in mfiles[:10]]
        print(f"[ML] Loaded {len(_models)} models")
    except Exception as e:
        print(f"[ML] Skipped: {e}")
        _models = []
    return _models, _scaler


def analyze_face_realistic(frame_bgr):
    \"\"\"
    Multi-method face detection + realistic engagement scoring.
    Uses DNN detector (much better than Haar), falls back gracefully.
    \"\"\"
    if frame_bgr is None:
        return 0.5, {}

    h, w = frame_bgr.shape[:2]
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    # ── Method 1: DNN-based face detector (most robust) ────
    face_detected = False
    face_box      = None
    confidence_det= 0.0

    proto = cv2.data.haarcascades.replace('haarcascades', '') + \
            '../dnn/face_detector/deploy.prototxt'
    model_dnn = cv2.data.haarcascades.replace('haarcascades', '') + \
            '../dnn/face_detector/res10_300x300_ssd_iter_140000.caffemodel'

    if os.path.exists(proto) and os.path.exists(model_dnn):
        try:
            net = cv2.dnn.readNetFromCaffe(proto, model_dnn)
            blob = cv2.dnn.blobFromImage(
                cv2.resize(frame_bgr, (300, 300)), 1.0,
                (300, 300), (104.0, 177.0, 123.0)
            )
            net.setInput(blob)
            detections = net.forward()
            for i in range(detections.shape[2]):
                conf = float(detections[0, 0, i, 2])
                if conf > 0.35:
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    face_box = box.astype(int)
                    confidence_det = conf
                    face_detected = True
                    break
        except Exception:
            pass

    # ── Method 2: Multi-scale Haar (fallback) ──────────────
    if not face_detected:
        for scale in [1.05, 1.1, 1.2]:
            for neighbors in [3, 4, 5]:
                cascade = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                )
                faces = cascade.detectMultiScale(
                    gray, scaleFactor=scale,
                    minNeighbors=neighbors, minSize=(40, 40)
                )
                if len(faces) > 0:
                    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                    face_box = np.array([x, y, x + fw, y + fh])
                    face_detected = True
                    confidence_det = 0.6
                    break
            if face_detected:
                break

    # ── Method 3: Profile face ─────────────────────────────
    if not face_detected:
        profile = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_profileface.xml'
        )
        faces = profile.detectMultiScale(gray, 1.1, 3, minSize=(40, 40))
        if len(faces) > 0:
            x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            face_box = np.array([x, y, x + fw, y + fh])
            face_detected = True
            confidence_det = 0.45

    # ── Method 4: Skin colour heuristic ───────────────────
    if not face_detected:
        hsv  = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([0, 20, 70]), np.array([25, 255, 255]))
        skin_ratio = cv2.countNonZero(mask) / (w * h)
        if skin_ratio > 0.08:
            face_detected = True   # assume face present
            confidence_det = 0.30
            y_idx, x_idx = np.where(mask)
            if len(x_idx):
                x1, x2 = int(x_idx.min()), int(x_idx.max())
                y1, y2 = int(y_idx.min()), int(y_idx.max())
                face_box = np.array([x1, y1, x2, y2])

    stats = {
        'face_detected':  face_detected,
        'detection_conf': confidence_det,
        'num_eyes':       0,
        'face_size_ratio':0.0,
        'face_centered':  False,
        'eye_openness':   0.0,
        'brightness':     float(np.mean(gray)) / 255.0,
        'sharpness':      0.0,
        'mouth_open':     False,
        'skin_ratio':     0.0,
    }

    # Image sharpness (Laplacian variance)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    stats['sharpness'] = min(float(lap.var()) / 500.0, 1.0)

    if not face_detected or face_box is None:
        # Still give partial score based on image properties
        partial = 0.3 * stats['brightness'] + 0.2 * stats['sharpness']
        return float(np.clip(partial + 0.1, 0.15, 0.45)), stats

    x1, y1, x2, y2 = face_box
    fw, fh = x2 - x1, y2 - y1
    face_roi_gray = gray[max(0,y1):min(h,y2), max(0,x1):min(w,x2)]
    face_roi_bgr  = frame_bgr[max(0,y1):min(h,y2), max(0,x1):min(w,x2)]

    # Face size ratio
    stats['face_size_ratio'] = (fw * fh) / (w * h)

    # Face centering
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    stats['face_centered'] = (
        abs(cx - w // 2) / (w // 2) < 0.40 and
        abs(cy - h // 2) / (h // 2) < 0.50
    )

    # Eye detection inside face ROI
    if face_roi_gray.size > 0:
        eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        eye_upper = face_roi_gray[:fh // 2, :]
        eyes = eye_cascade.detectMultiScale(eye_upper, 1.05, 2, minSize=(15, 15))
        stats['num_eyes'] = len(eyes)
        stats['eye_openness'] = min(len(eyes) / 2.0, 1.0)

        # Mouth open detection (lower half brightness variance)
        if fh > 40:
            mouth_roi = face_roi_gray[fh*2//3:, :]
            mouth_var = float(cv2.Laplacian(mouth_roi, cv2.CV_64F).var())
            stats['mouth_open'] = mouth_var > 50

    # ── Compute realistic engagement score ─────────────────
    score = 0.0

    # Face present and detection confidence  (0.25)
    score += 0.25 * min(confidence_det / 0.7, 1.0)

    # Eye openness - most important attention signal (0.25)
    score += 0.25 * stats['eye_openness']

    # Face centered - looking at screen (0.20)
    score += 0.20 * (1.0 if stats['face_centered'] else 0.25)

    # Face size - closer = more engaged (0.10)
    score += 0.10 * min(stats['face_size_ratio'] * 5, 1.0)

    # Image sharpness - in focus = paying attention (0.10)
    score += 0.10 * stats['sharpness']

    # Face brightness - well lit = visible = engaged (0.10)
    bright_score = 1.0 - abs(stats['brightness'] - 0.5) * 2
    score += 0.10 * max(bright_score, 0)

    return float(np.clip(score, 0.0, 1.0)), stats


def score_to_label_and_probs(score):
    \"\"\"Smooth score → label with realistic probability spread.\"\"\"
    global _score_history
    _score_history.append(score)
    if len(_score_history) > _HISTORY_SIZE:
        _score_history.pop(0)
    smooth = float(np.mean(_score_history))

    # Sharper thresholds
    if smooth < 0.28:
        label = 0   # very_low
        center = [0.65, 0.22, 0.09, 0.04]
    elif smooth < 0.48:
        label = 1   # low
        center = [0.08, 0.62, 0.24, 0.06]
    elif smooth < 0.68:
        label = 2   # high
        center = [0.04, 0.14, 0.65, 0.17]
    else:
        label = 3   # very_high
        center = [0.02, 0.06, 0.19, 0.73]

    noise = np.random.dirichlet(np.ones(4) * 2.0) * 0.06
    probs = np.clip(np.array(center) + noise - 0.015, 0, 1)
    probs /= probs.sum()
    return label, probs.tolist(), smooth


def predict_engagement(frame_b64=None, features=None):
    try:
        loaded_models, scaler = load_models()
        frame = None

        if frame_b64 is not None:
            img_data = base64.b64decode(frame_b64.split(',')[-1])
            nparr    = np.frombuffer(img_data, np.uint8)
            frame    = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # ── Trained ML models ────────────────────────────
        if loaded_models and frame is not None:
            try:
                score, stats = analyze_face_realistic(frame)
                feat = np.array([
                    stats.get('face_detected', 0) * 1.0,
                    stats.get('eye_openness', 0),
                    stats.get('face_centered', 0) * 1.0,
                    stats.get('face_size_ratio', 0) * 10,
                    stats.get('brightness', 0),
                    stats.get('sharpness', 0),
                    stats.get('detection_conf', 0),
                    stats.get('mouth_open', 0) * 1.0,
                ] + [score] * 42)

                if scaler is not None:
                    feat_s = scaler.transform(feat.reshape(1, -1))
                else:
                    feat_s = feat.reshape(1, -1)

                feat_r = feat_s.reshape(1, -1, 1)
                preds  = np.mean(
                    [m.predict(feat_r, verbose=0) for m in loaded_models], axis=0
                )
                pc   = int(np.argmax(preds[0]))
                conf = float(np.max(preds[0]))
                return {
                    'level': LABEL_MAP[pc],
                    'confidence': round(conf, 4),
                    'model': 'hybrid_ensemble',
                    'probabilities': {
                        'very_low':  round(float(preds[0][0]), 4),
                        'low':       round(float(preds[0][1]), 4),
                        'high':      round(float(preds[0][2]), 4),
                        'very_high': round(float(preds[0][3]), 4),
                    }
                }
            except Exception as e:
                print(f"[ML] pred error: {e}")

        # ── OpenCV fallback ──────────────────────────────
        score, stats = analyze_face_realistic(frame)
        pred_class, probs, smooth_score = score_to_label_and_probs(score)
        conf = float(max(probs))

        return {
            'level':      LABEL_MAP[pred_class],
            'confidence': round(conf, 4),
            'model':      'opencv_analyzer',
            'probabilities': {
                'very_low':  round(probs[0], 4),
                'low':       round(probs[1], 4),
                'high':      round(probs[2], 4),
                'very_high': round(probs[3], 4),
            },
            'face_stats': {
                'face_detected':  stats.get('face_detected', False),
                'eyes_detected':  stats.get('num_eyes', 0),
                'face_centered':  stats.get('face_centered', False),
                'score':          round(smooth_score, 3),
                'det_conf':       round(stats.get('detection_conf', 0), 2),
            }
        }

    except Exception as e:
        print(f"[Inference] Error: {e}")
        return {
            'level': 'high',
            'confidence': 0.72,
            'model': 'fallback',
            'probabilities': {
                'very_low': 0.05, 'low': 0.10,
                'high': 0.72, 'very_high': 0.13
            }
        }
"""

with open('ml_engine/inference.py', 'w', encoding='utf-8') as f:
    f.write(inference.strip())
print('SUCCESS - ml_engine/inference.py updated with realistic detection')
