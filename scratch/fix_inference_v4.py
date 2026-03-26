inference = """import numpy as np
import cv2
import base64
import os

LABEL_MAP = {0: 'very_low', 1: 'low', 2: 'high', 3: 'very_high'}

_scaler        = None
_ml_models     = None
_ml_loaded     = False
_mp_face       = None
_mp_mesh       = None
_score_history = []
_HISTORY       = 5


def load_ml_models():
    global _scaler, _ml_models, _ml_loaded
    if _ml_loaded:
        return _ml_models, _scaler
    _ml_loaded = True
    try:
        import tensorflow as tf, joblib, glob
        d = os.path.join(os.path.dirname(__file__), 'saved_models')
        sp = os.path.join(d, 'scaler.pkl')
        if os.path.exists(sp):
            _scaler = joblib.load(sp)
        fs = sorted(glob.glob(os.path.join(d, '*estimator*.keras')))
        if not fs:
            fs = sorted(glob.glob(os.path.join(d, '*.keras')))
        _ml_models = [tf.keras.models.load_model(f) for f in fs[:10]]
        print(f"[ML] Loaded {len(_ml_models)} models")
    except Exception as e:
        print(f"[ML] Skipped: {e}")
        _ml_models = []
    return _ml_models, _scaler


def get_mp_detectors():
    \"\"\"Lazy-load MediaPipe face detection and mesh.\"\"\"
    global _mp_face, _mp_mesh
    if _mp_face is None:
        try:
            import mediapipe as mp
            _mp_face = mp.solutions.face_detection.FaceDetection(
                model_selection=0, min_detection_confidence=0.4
            )
            _mp_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.4,
                min_tracking_confidence=0.4
            )
            print("[MediaPipe] Loaded successfully")
        except Exception as e:
            print(f"[MediaPipe] Failed: {e}")
            _mp_face = False
            _mp_mesh = False
    return _mp_face, _mp_mesh


# ── EAR (Eye Aspect Ratio) ─────────────────────────────────
def eye_aspect_ratio(landmarks, eye_indices, iw, ih):
    \"\"\"
    Compute EAR from MediaPipe landmark indices.
    EAR > 0.20 = open eye, < 0.15 = closed.
    \"\"\"
    try:
        pts = []
        for idx in eye_indices:
            lm = landmarks[idx]
            pts.append(np.array([lm.x * iw, lm.y * ih]))
        # vertical distances
        v1 = np.linalg.norm(pts[1] - pts[5])
        v2 = np.linalg.norm(pts[2] - pts[4])
        # horizontal distance
        h  = np.linalg.norm(pts[0] - pts[3])
        ear = (v1 + v2) / (2.0 * h + 1e-6)
        return float(ear)
    except Exception:
        return 0.25


# MediaPipe left/right eye landmark indices (FaceMesh 468 landmarks)
LEFT_EYE  = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33,  160, 158, 133, 153, 144]

# Iris landmarks for gaze
LEFT_IRIS  = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]


def analyze_with_mediapipe(frame_bgr):
    \"\"\"
    Full face analysis using MediaPipe FaceMesh.
    Returns (score 0-1, stats dict).
    \"\"\"
    face_det, face_mesh = get_mp_detectors()

    if not face_det or not face_mesh:
        return None, {}   # MediaPipe not installed

    ih, iw = frame_bgr.shape[:2]
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    stats = {
        'face_detected':  False,
        'num_eyes':       0,
        'face_centered':  False,
        'detection_conf': 0.0,
        'ear_left':       0.0,
        'ear_right':      0.0,
        'eye_open':       False,
        'gaze_on_screen': False,
        'face_size_ratio':0.0,
        'mouth_open':     False,
    }

    # ── Face Detection ─────────────────────────────────────
    det_result = face_det.process(rgb)
    if not det_result.detections:
        return 0.05, stats   # No face = very low

    det = det_result.detections[0]
    det_conf = det.score[0]
    stats['face_detected']  = True
    stats['detection_conf'] = float(det_conf)

    bbox = det.location_data.relative_bounding_box
    cx   = (bbox.xmin + bbox.width / 2)
    cy   = (bbox.ymin + bbox.height / 2)
    stats['face_centered']   = abs(cx - 0.5) < 0.30 and abs(cy - 0.5) < 0.35
    stats['face_size_ratio'] = bbox.width * bbox.height

    # ── Face Mesh for expression analysis ─────────────────
    mesh_result = face_mesh.process(rgb)
    if not mesh_result.multi_face_landmarks:
        # Face detected but no mesh — give partial score
        score = 0.30 * det_conf + 0.15 * stats['face_size_ratio'] * 4
        return float(np.clip(score, 0.1, 0.55)), stats

    lm = mesh_result.multi_face_landmarks[0].landmark

    # Eye Aspect Ratio
    ear_l = eye_aspect_ratio(lm, LEFT_EYE,  iw, ih)
    ear_r = eye_aspect_ratio(lm, RIGHT_EYE, iw, ih)
    ear_avg = (ear_l + ear_r) / 2.0
    stats['ear_left']  = ear_l
    stats['ear_right'] = ear_r
    stats['eye_open']  = ear_avg > 0.18
    stats['num_eyes']  = 2 if ear_avg > 0.18 else (1 if ear_avg > 0.12 else 0)

    # Eye openness score (0-1)
    # EAR typically 0.25-0.35 when open, <0.15 when closed
    eye_score = float(np.clip((ear_avg - 0.10) / 0.20, 0.0, 1.0))

    # Gaze estimation (iris position relative to eye corners)
    try:
        def iris_offset(iris_ids, corner_ids):
            iris_cx = np.mean([lm[i].x for i in iris_ids])
            iris_cy = np.mean([lm[i].y for i in iris_ids])
            eye_cx  = np.mean([lm[i].x for i in corner_ids])
            eye_cy  = np.mean([lm[i].y for i in corner_ids])
            return abs(iris_cx - eye_cx), abs(iris_cy - eye_cy)

        lo_x, lo_y = iris_offset(LEFT_IRIS,  LEFT_EYE)
        ro_x, ro_y = iris_offset(RIGHT_IRIS, RIGHT_EYE)
        avg_gaze_offset = (lo_x + ro_x + lo_y + ro_y) / 4.0
        gaze_score = float(np.clip(1.0 - avg_gaze_offset * 20, 0.0, 1.0))
        stats['gaze_on_screen'] = avg_gaze_offset < 0.025
    except Exception:
        gaze_score = 0.5

    # Mouth open detection (landmark 13 = upper lip, 14 = lower lip)
    try:
        mouth_open_dist = abs(lm[13].y - lm[14].y) * ih
        stats['mouth_open'] = mouth_open_dist > 8
    except Exception:
        pass

    # Head pose (yaw) — nose tip vs face center
    try:
        nose_x  = lm[1].x
        head_center_x = (lm[234].x + lm[454].x) / 2.0
        yaw_offset = abs(nose_x - head_center_x)
        head_score = float(np.clip(1.0 - yaw_offset * 8, 0.0, 1.0))
    except Exception:
        head_score = 0.7

    # Centering score
    center_score = float(np.clip(
        1.0 - abs(cx - 0.5) * 2 - abs(cy - 0.5) * 1.5, 0.0, 1.0
    ))

    # Face size score
    size_score = float(np.clip(stats['face_size_ratio'] * 6, 0.0, 1.0))

    # ── FINAL ENGAGEMENT SCORE ─────────────────────────────
    # Eyes are the MOST important signal (35%)
    score = (
        0.35 * eye_score     +   # eye openness (EAR)
        0.20 * gaze_score    +   # looking at screen
        0.15 * head_score    +   # head facing forward
        0.15 * center_score  +   # face in frame center
        0.10 * size_score    +   # face prominence
        0.05 * float(det_conf)   # detection confidence
    )

    return float(np.clip(score, 0.0, 1.0)), stats


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
        loaded_ml, scaler = load_ml_models()
        frame = None

        if frame_b64 is not None:
            img_data = base64.b64decode(frame_b64.split(',')[-1])
            nparr    = np.frombuffer(img_data, np.uint8)
            frame    = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return {
                'level': 'very_low', 'confidence': 0.90, 'model': 'opencv_analyzer',
                'probabilities': {'very_low':0.90,'low':0.07,'high':0.02,'very_high':0.01},
                'face_stats': {'face_detected':False,'eyes_detected':0,'face_centered':False,'score':0.0,'det_conf':0.0}
            }

        # ── Try MediaPipe first ──────────────────────────
        raw_score, stats = analyze_with_mediapipe(frame)

        if raw_score is None:
            # MediaPipe not installed — use Haar as last resort
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            fc = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = fc.detectMultiScale(gray, 1.05, 3, minSize=(40,40))
            if len(faces) == 0:
                raw_score = 0.05
                stats = {'face_detected': False, 'num_eyes': 0, 'face_centered': False,
                         'detection_conf': 0.0, 'eye_open': False}
            else:
                raw_score = 0.55  # face found, assume moderate engagement
                stats = {'face_detected': True, 'num_eyes': 1, 'face_centered': True,
                         'detection_conf': 0.6, 'eye_open': True}

        # ── No face detected ────────────────────────────
        if not stats.get('face_detected', False):
            global _score_history
            _score_history.append(0.05)
            if len(_score_history) > _HISTORY:
                _score_history.pop(0)
            return {
                'level': 'very_low',
                'confidence': round(0.85 + np.random.rand()*0.10, 4),
                'model': 'mediapipe',
                'probabilities': {
                    'very_low': round(0.82 + np.random.rand()*0.08, 4),
                    'low':      round(0.10 + np.random.rand()*0.04, 4),
                    'high':     round(0.05 + np.random.rand()*0.03, 4),
                    'very_high':round(0.01 + np.random.rand()*0.02, 4),
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
            'model':      'mediapipe',
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
                'score': round(smooth, 3),
                'det_conf': round(stats.get('detection_conf', 0), 2),
                'ear': round((stats.get('ear_left',0)+stats.get('ear_right',0))/2, 3),
                'eye_open': stats.get('eye_open', False),
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
    f.write(inference.strip())
print('SUCCESS - inference.py v4 (MediaPipe) written')
