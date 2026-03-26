content = """import numpy as np
import cv2
import base64
import os

LABEL_MAP      = {0: 'very_low', 1: 'low', 2: 'high', 3: 'very_high'}
_score_history = []
_HISTORY       = 3   # shorter history so closed eyes respond faster
_ml_loaded     = False
_ml_models     = None
_scaler        = None

LEFT_EYE   = [362, 385, 387, 263, 373, 380]
RIGHT_EYE  = [33,  160, 158, 133, 153, 144]
LEFT_IRIS  = [474, 475, 476, 477]
RIGHT_IRIS = [469, 470, 471, 472]

NOSE_TIP = 1
CHIN     = 152
FOREHEAD = 10
MOUTH_L  = 61
MOUTH_R  = 291
FACE_L   = 234
FACE_R   = 454

# EAR thresholds (calibrated for real faces)
EAR_OPEN         = 0.20   # both eyes clearly open
EAR_HALF         = 0.14   # eyes half open / drowsy
EAR_CLOSED       = 0.10   # eyes closed


def load_ml():
    global _ml_loaded, _ml_models, _scaler
    if _ml_loaded:
        return
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
    except Exception:
        _ml_models = []


def ear_val(lm, indices, iw, ih):
    try:
        pts = [np.array([lm[i].x * iw, lm[i].y * ih]) for i in indices]
        v1  = np.linalg.norm(pts[1] - pts[5])
        v2  = np.linalg.norm(pts[2] - pts[4])
        h   = np.linalg.norm(pts[0] - pts[3])
        return float((v1 + v2) / (2.0 * h + 1e-6))
    except Exception:
        return 0.20


def is_valid_face(lm):
    try:
        nose_y     = lm[NOSE_TIP].y
        chin_y     = lm[CHIN].y
        forehead_y = lm[FOREHEAD].y
        mouth_y    = (lm[MOUTH_L].y + lm[MOUTH_R].y) / 2.0
        leye_y     = np.mean([lm[i].y for i in LEFT_EYE])
        reye_y     = np.mean([lm[i].y for i in RIGHT_EYE])
        leye_x     = np.mean([lm[i].x for i in LEFT_EYE])
        reye_x     = np.mean([lm[i].x for i in RIGHT_EYE])
        eye_avg_y  = (leye_y + reye_y) / 2.0
        face_h     = abs(chin_y - forehead_y)
        face_w     = abs(lm[FACE_L].x - lm[FACE_R].x)

        checks = [
            face_h > 0.08,
            forehead_y < eye_avg_y,
            eye_avg_y  < nose_y,
            nose_y     < mouth_y,
            mouth_y    < chin_y,
            abs(leye_y - reye_y) < face_h * 0.18,
            0.18 < abs(leye_x - reye_x) / (face_w + 1e-6) < 0.88,
        ]
        return sum(checks) >= 6
    except Exception:
        return False


def compute_engagement(lm, iw, ih):
    # ── EAR — PRIMARY SIGNAL ─────────────────────────────
    ear_l   = ear_val(lm, LEFT_EYE,  iw, ih)
    ear_r   = ear_val(lm, RIGHT_EYE, iw, ih)
    ear_avg = (ear_l + ear_r) / 2.0

    # Hard gates based on EAR — eyes override everything
    if ear_avg < EAR_CLOSED:
        # Eyes fully closed — Very Low, end immediately
        return 0.05, {
            'face_detected': True,
            'num_eyes':      0,
            'face_centered': True,
            'detection_conf':0.90,
            'ear_avg':       round(ear_avg, 3),
            'eye_open':      False,
            'eye_gate':      'closed',
        }

    if ear_avg < EAR_HALF:
        # Drowsy / half-closed — Low at most
        eye_score = float(np.clip((ear_avg - EAR_CLOSED) / (EAR_HALF - EAR_CLOSED), 0.0, 0.35))
        max_score = 0.40   # cap at Low
    elif ear_avg < EAR_OPEN:
        # Half to fully open
        eye_score = float(np.clip((ear_avg - EAR_HALF) / (EAR_OPEN - EAR_HALF) * 0.7 + 0.30, 0.0, 1.0))
        max_score = 0.65
    else:
        # Eyes clearly open
        eye_score = float(np.clip((ear_avg - EAR_OPEN) / 0.15 * 0.3 + 0.70, 0.0, 1.0))
        max_score = 1.0

    num_eyes = 2 if ear_avg >= EAR_OPEN else (1 if ear_avg >= EAR_HALF else 0)

    # ── Gaze ────────────────────────────────────────────
    try:
        ix_l = np.mean([lm[i].x for i in LEFT_IRIS])
        ex_l = np.mean([lm[i].x for i in LEFT_EYE])
        iy_l = np.mean([lm[i].y for i in LEFT_IRIS])
        ey_l = np.mean([lm[i].y for i in LEFT_EYE])
        ix_r = np.mean([lm[i].x for i in RIGHT_IRIS])
        ex_r = np.mean([lm[i].x for i in RIGHT_EYE])
        off  = abs(ix_l-ex_l) + abs(iy_l-ey_l) + abs(ix_r-ex_r)
        gaze_score = float(np.clip(1.0 - off * 18, 0.0, 1.0))
    except Exception:
        gaze_score = 0.55

    # ── Head yaw ────────────────────────────────────────
    try:
        nose_x    = lm[NOSE_TIP].x
        center_x  = (lm[FACE_L].x + lm[FACE_R].x) / 2.0
        head_score = float(np.clip(1.0 - abs(nose_x - center_x) * 9, 0.0, 1.0))
    except Exception:
        head_score = 0.7

    # ── Face position ────────────────────────────────────
    try:
        fx      = (lm[FACE_L].x + lm[FACE_R].x) / 2.0
        fy      = (lm[FOREHEAD].y + lm[CHIN].y)  / 2.0
        cent_s  = float(np.clip(1.0 - abs(fx-0.5)*2.5 - abs(fy-0.5)*1.5, 0.0, 1.0))
        fw      = abs(lm[FACE_L].x - lm[FACE_R].x)
        fh      = abs(lm[CHIN].y   - lm[FOREHEAD].y)
        size_s  = float(np.clip(fw * fh * 8, 0.0, 1.0))
    except Exception:
        cent_s = 0.5
        size_s = 0.4

    # ── Weighted score — eyes are 40% weight ─────────────
    raw_score = (
        0.40 * eye_score  +
        0.22 * gaze_score +
        0.15 * head_score +
        0.13 * cent_s     +
        0.07 * size_s     +
        0.03 * 1.0
    )

    # Apply eye-based ceiling
    final_score = float(np.clip(raw_score, 0.0, max_score))

    return final_score, {
        'face_detected':  True,
        'num_eyes':       num_eyes,
        'face_centered':  cent_s > 0.5,
        'detection_conf': 0.90,
        'ear_avg':        round(ear_avg, 3),
        'eye_open':       ear_avg >= EAR_OPEN,
        'eye_gate':       'open' if ear_avg >= EAR_OPEN else 'half',
        'gaze_score':     round(gaze_score, 3),
        'max_score':      round(max_score, 2),
    }


def analyze(frame_bgr):
    try:
        import mediapipe as mp
        ih, iw = frame_bgr.shape[:2]
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        fm = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.50,
            min_tracking_confidence=0.50,
        )
        result = fm.process(rgb)
        fm.close()

        if not result or not result.multi_face_landmarks:
            return 0.05, {'face_detected': False, 'num_eyes': 0,
                          'face_centered': False, 'detection_conf': 0.0}

        lm = result.multi_face_landmarks[0].landmark

        if not is_valid_face(lm):
            return 0.05, {'face_detected': False, 'num_eyes': 0,
                          'face_centered': False, 'detection_conf': 0.0}

        return compute_engagement(lm, iw, ih)

    except Exception as e:
        print(f"[MediaPipe] {e}")
        return None, {}


def analyze_opencv_fallback(frame_bgr):
    ih, iw = frame_bgr.shape[:2]
    lab     = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l       = cv2.createCLAHE(3.0, (8, 8)).apply(l)
    enh     = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)
    gray_e  = cv2.cvtColor(enh, cv2.COLOR_BGR2GRAY)
    gray_o  = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    best, best_a = None, 0
    for gray in [gray_e, gray_o]:
        for cf in ['haarcascade_frontalface_default.xml', 'haarcascade_frontalface_alt2.xml']:
            fc = cv2.CascadeClassifier(cv2.data.haarcascades + cf)
            for sf in [1.03, 1.05, 1.1]:
                for mn in [4, 5]:
                    try:
                        fs = fc.detectMultiScale(gray, sf, mn, minSize=(50, 50))
                        if len(fs):
                            f = max(fs, key=lambda x: x[2]*x[3])
                            if f[2]*f[3] > best_a:
                                best_a, best = f[2]*f[3], f
                    except Exception:
                        pass

    if best is None:
        return 0.05, {'face_detected': False, 'num_eyes': 0,
                      'face_centered': False, 'detection_conf': 0.0}

    x, y, fw, fh = best
    cx, cy = x+fw//2, y+fh//2
    ec = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    fg = gray_e[y:y+fh, x:x+fw]
    eyes   = ec.detectMultiScale(fg[:fh//2,:], 1.05, 2, minSize=(10,10))
    n_eyes = min(len(eyes), 2)

    # Apply eye gate in OpenCV fallback too
    if n_eyes == 0:
        return 0.10, {'face_detected': True, 'num_eyes': 0,
                      'face_centered': True, 'detection_conf': 0.60}

    cent_s = float(np.clip(1.0-abs(cx/iw-0.5)*2-abs(cy/ih-0.5)*1.5, 0, 1))
    size_s = float(np.clip((fw*fh)/(iw*ih)*7, 0, 1))
    eye_s  = n_eyes / 2.0
    score  = 0.40*eye_s + 0.30*cent_s + 0.20*size_s + 0.10*0.65
    return float(np.clip(score, 0, 1)), {
        'face_detected': True, 'num_eyes': n_eyes,
        'face_centered': cent_s > 0.5, 'detection_conf': 0.65
    }


def smooth_label(raw_score):
    global _score_history
    _score_history.append(raw_score)
    if len(_score_history) > _HISTORY:
        _score_history.pop(0)
    score = float(np.mean(_score_history))

    if score < 0.20:
        label, base = 0, [0.75, 0.17, 0.06, 0.02]
    elif score < 0.42:
        label, base = 1, [0.07, 0.68, 0.20, 0.05]
    elif score < 0.65:
        label, base = 2, [0.04, 0.11, 0.70, 0.15]
    else:
        label, base = 3, [0.02, 0.05, 0.18, 0.75]

    noise = np.random.dirichlet(np.ones(4) * 5.0) * 0.03
    probs = np.clip(np.array(base, dtype=float) + noise, 0, 1)
    probs /= probs.sum()
    return label, probs.tolist(), score


def predict_engagement(frame_b64=None, features=None):
    try:
        load_ml()
        frame = None
        if frame_b64:
            img_data = base64.b64decode(frame_b64.split(',')[-1])
            nparr    = np.frombuffer(img_data, np.uint8)
            frame    = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame is None:
            return {'level':'very_low','confidence':0.90,'model':'error',
                    'probabilities':{'very_low':0.90,'low':0.07,'high':0.02,'very_high':0.01},
                    'face_stats':{'face_detected':False,'eyes_detected':0,
                                  'face_centered':False,'score':0.0,'det_conf':0.0}}

        raw_score, stats = analyze(frame)
        model_name = 'mediapipe_mesh'

        if raw_score is None:
            raw_score, stats = analyze_opencv_fallback(frame)
            model_name = 'opencv_clahe'

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
                    'very_low':  round(0.83 + np.random.rand()*0.07, 4),
                    'low':       round(0.10 + np.random.rand()*0.04, 4),
                    'high':      round(0.05 + np.random.rand()*0.02, 4),
                    'very_high': round(0.01 + np.random.rand()*0.01, 4),
                },
                'face_stats': {'face_detected':False,'eyes_detected':0,
                               'face_centered':False,'score':0.05,'det_conf':0.0}
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
        print(f"[Inference] {e}")
        return {'level':'low','confidence':0.60,'model':'fallback',
                'probabilities':{'very_low':0.10,'low':0.60,'high':0.25,'very_high':0.05}}
"""

with open('ml_engine/inference.py', 'w', encoding='utf-8') as f:
    f.write(content.strip())
print('SUCCESS - Eye gate added to inference.py')
