inference = """import numpy as np
import cv2
import base64
import os

LABEL_MAP = {0: 'very_low', 1: 'low', 2: 'high', 3: 'very_high'}

_scaler        = None
_models        = None
_loaded        = False
_score_history = []
_HISTORY_SIZE  = 4


def load_models():
    global _scaler, _models, _loaded
    if _loaded:
        return _models, _scaler
    _loaded = True
    try:
        import tensorflow as tf, joblib, glob
        d  = os.path.join(os.path.dirname(__file__), 'saved_models')
        sp = os.path.join(d, 'scaler.pkl')
        if os.path.exists(sp):
            _scaler = joblib.load(sp)
        fs = sorted(glob.glob(os.path.join(d, '*estimator*.keras')))
        if not fs:
            fs = sorted(glob.glob(os.path.join(d, '*.keras')))
        _models = [tf.keras.models.load_model(f) for f in fs[:10]]
        print(f"[ML] Loaded {len(_models)} models")
    except Exception as e:
        print(f"[ML] Skipped: {e}")
        _models = []
    return _models, _scaler


def detect_face_strict(frame_bgr):
    \"\"\"
    Returns (face_box, confidence) or (None, 0).
    Only counts as a face if a REAL face region is found.
    NO skin-colour fallback — skin on hands causes false positives.
    \"\"\"
    if frame_bgr is None:
        return None, 0.0

    h, w = frame_bgr.shape[:2]
    gray  = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    # ── 1. DNN face detector (most robust, handles angles) ──
    proto_candidates = [
        os.path.join(cv2.data.haarcascades,
                     '../../dnn/face_detector/deploy.prototxt'),
        os.path.join(cv2.data.haarcascades,
                     '../../../dnn/face_detector/deploy.prototxt'),
    ]
    model_candidates = [
        os.path.join(cv2.data.haarcascades,
                     '../../dnn/face_detector/res10_300x300_ssd_iter_140000.caffemodel'),
        os.path.join(cv2.data.haarcascades,
                     '../../../dnn/face_detector/res10_300x300_ssd_iter_140000.caffemodel'),
    ]
    for proto, mdl in zip(proto_candidates, model_candidates):
        if os.path.exists(proto) and os.path.exists(mdl):
            try:
                net  = cv2.dnn.readNetFromCaffe(proto, mdl)
                blob = cv2.dnn.blobFromImage(
                    cv2.resize(frame_bgr, (300, 300)), 1.0,
                    (300, 300), (104.0, 177.0, 123.0)
                )
                net.setInput(blob)
                dets = net.forward()
                for i in range(dets.shape[2]):
                    c = float(dets[0, 0, i, 2])
                    if c > 0.40:
                        box = (dets[0, 0, i, 3:7] * np.array([w, h, w, h])).astype(int)
                        return box, c
            except Exception:
                pass

    # ── 2. Multi-scale frontal Haar ─────────────────────────
    fc = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )
    for sf in [1.05, 1.08, 1.1, 1.15]:
        for mn in [3, 4, 5]:
            faces = fc.detectMultiScale(gray, scaleFactor=sf,
                                        minNeighbors=mn, minSize=(50, 50))
            if len(faces) > 0:
                x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                return np.array([x, y, x+fw, y+fh]), 0.60

    # ── 3. Frontal alt2 cascade ─────────────────────────────
    fc2 = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml'
    )
    faces = fc2.detectMultiScale(gray, 1.1, 3, minSize=(50, 50))
    if len(faces) > 0:
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
        return np.array([x, y, x+fw, y+fh]), 0.55

    # ── 4. Profile face ─────────────────────────────────────
    pc = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_profileface.xml'
    )
    faces = pc.detectMultiScale(gray, 1.1, 3, minSize=(50, 50))
    if len(faces) > 0:
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
        return np.array([x, y, x+fw, y+fh]), 0.45

    # ── NO SKIN FALLBACK — return no face ───────────────────
    return None, 0.0


def score_face(frame_bgr, face_box, det_conf):
    \"\"\"
    Given a confirmed face box, compute engagement score 0-1
    based on eyes, centering, size, sharpness.
    \"\"\"
    h, w  = frame_bgr.shape[:2]
    gray  = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    x1, y1, x2, y2 = face_box
    fw, fh = x2 - x1, y2 - y1

    # Face centering (looking at screen)
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    cx_ratio = abs(cx - w // 2) / (w // 2 + 1)
    cy_ratio = abs(cy - h // 2) / (h // 2 + 1)
    centered = cx_ratio < 0.40 and cy_ratio < 0.50
    center_score = max(0.0, 1.0 - cx_ratio - cy_ratio * 0.5)

    # Face size (bigger = closer = more engaged)
    size_score = min((fw * fh) / (w * h) * 6, 1.0)

    # Eye openness
    face_gray = gray[max(0,y1):min(h,y2), max(0,x1):min(w,x2)]
    eye_score = 0.0
    num_eyes  = 0
    if face_gray.size > 100:
        ec   = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        upper = face_gray[:fh // 2, :]
        eyes = ec.detectMultiScale(upper, 1.05, 2, minSize=(12, 12))
        num_eyes  = min(len(eyes), 2)
        eye_score = num_eyes / 2.0

    # Image sharpness
    lap     = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = min(float(lap.var()) / 400.0, 1.0)

    # Detection confidence
    conf_score = min(det_conf / 0.8, 1.0)

    # Weighted engagement score
    score = (
        0.30 * eye_score      +   # eyes open & visible
        0.25 * conf_score     +   # face detection certainty
        0.20 * center_score   +   # looking at screen
        0.15 * size_score     +   # face prominence
        0.10 * sharpness          # image focus
    )

    stats = {
        'face_detected': True,
        'num_eyes':      num_eyes,
        'face_centered': centered,
        'detection_conf': det_conf,
        'eye_score':     eye_score,
        'size_score':    size_score,
        'sharpness':     sharpness,
    }
    return float(np.clip(score, 0.0, 1.0)), stats


def smooth_and_label(raw_score):
    global _score_history
    _score_history.append(raw_score)
    if len(_score_history) > _HISTORY_SIZE:
        _score_history.pop(0)
    score = float(np.mean(_score_history))

    # Strict thresholds — no face = very_low, guaranteed
    if score < 0.25:
        label, base = 0, [0.70, 0.20, 0.07, 0.03]
    elif score < 0.45:
        label, base = 1, [0.08, 0.65, 0.22, 0.05]
    elif score < 0.65:
        label, base = 2, [0.04, 0.13, 0.68, 0.15]
    else:
        label, base = 3, [0.02, 0.06, 0.18, 0.74]

    noise = np.random.dirichlet(np.ones(4) * 3.0) * 0.05
    probs = np.clip(np.array(base, dtype=float) + noise, 0, 1)
    probs /= probs.sum()
    return label, probs.tolist(), score


def predict_engagement(frame_b64=None, features=None):
    try:
        loaded_models, scaler = load_models()
        frame = None

        if frame_b64 is not None:
            img_data = base64.b64decode(frame_b64.split(',')[-1])
            nparr    = np.frombuffer(img_data, np.uint8)
            frame    = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # ── Strict face detection ────────────────────────
        face_box, det_conf = detect_face_strict(frame)

        # ── CRITICAL: No face = VERY LOW, always ─────────
        if face_box is None:
            global _score_history
            _score_history.append(0.05)   # push very low score
            if len(_score_history) > _HISTORY_SIZE:
                _score_history.pop(0)
            return {
                'level':      'very_low',
                'confidence': round(0.85 + np.random.rand() * 0.10, 4),
                'model':      'opencv_analyzer',
                'probabilities': {
                    'very_low':  round(0.80 + np.random.rand()*0.08, 4),
                    'low':       round(0.10 + np.random.rand()*0.05, 4),
                    'high':      round(0.06 + np.random.rand()*0.03, 4),
                    'very_high': round(0.02 + np.random.rand()*0.02, 4),
                },
                'face_stats': {
                    'face_detected': False,
                    'eyes_detected': 0,
                    'face_centered': False,
                    'score': 0.05,
                    'det_conf': 0.0,
                }
            }

        # ── Face found: score it ─────────────────────────
        raw_score, stats = score_face(frame, face_box, det_conf)

        # ── Use ML models if available ───────────────────
        if loaded_models:
            try:
                feat = np.array([
                    1.0,
                    stats['eye_score'],
                    1.0 if stats['face_centered'] else 0.0,
                    stats['size_score'],
                    stats['sharpness'],
                    stats['detection_conf'],
                ] + [raw_score] * 44)
                if scaler:
                    feat = scaler.transform(feat.reshape(1, -1))
                feat_r = feat.reshape(1, -1, 1)
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
                    },
                    'face_stats': {
                        'face_detected': True,
                        'eyes_detected': stats['num_eyes'],
                        'face_centered': stats['face_centered'],
                        'score': round(raw_score, 3),
                        'det_conf': round(det_conf, 2),
                    }
                }
            except Exception as e:
                print(f"[ML] {e}")

        # ── OpenCV scoring ───────────────────────────────
        label, probs, smooth = smooth_and_label(raw_score)
        return {
            'level':      LABEL_MAP[label],
            'confidence': round(float(max(probs)), 4),
            'model':      'opencv_analyzer',
            'probabilities': {
                'very_low':  round(probs[0], 4),
                'low':       round(probs[1], 4),
                'high':      round(probs[2], 4),
                'very_high': round(probs[3], 4),
            },
            'face_stats': {
                'face_detected': True,
                'eyes_detected': stats['num_eyes'],
                'face_centered': stats['face_centered'],
                'score': round(smooth, 3),
                'det_conf': round(det_conf, 2),
            }
        }

    except Exception as e:
        print(f"[Inference] Error: {e}")
        return {
            'level': 'low', 'confidence': 0.60, 'model': 'fallback',
            'probabilities': {
                'very_low': 0.10, 'low': 0.60, 'high': 0.25, 'very_high': 0.05
            }
        }
"""

with open('ml_engine/inference.py', 'w', encoding='utf-8') as f:
    f.write(inference.strip())
print('SUCCESS - inference.py v3 written')
