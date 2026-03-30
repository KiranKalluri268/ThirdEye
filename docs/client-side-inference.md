# Client-Side Inference Migration Guide

**ThirdEyeAI — Moving from Server-Side to Browser-Side Engagement Detection**

---

## Overview

Currently, ThirdEyeAI sends a raw JPEG frame (~50–100 KB) to the Django server every 3 seconds per student. The server runs MediaPipe FaceMesh + engagement scoring and returns a prediction. This approach does not scale beyond ~30 concurrent users on a single server.

This document describes how to migrate the inference pipeline entirely into the **student's browser** using:

- **MediaPipe Tasks Vision (WASM/WebGL)** — replaces `mediapipe` Python library
- **TensorFlow.js** — replaces `tensorflow` / Keras `.keras` models
- **Vanilla JavaScript** — replaces `inference.py` math (EAR, gaze, head yaw)

After migration, the server's only role is **authentication + saving small JSON results to the database**. No raw video or ML computation happens server-side.

---

## Architecture Comparison

### Before (Current — Server-Side)

```
Browser                           Django Server
───────────────                   ─────────────────────────────────
📹 Webcam
  │ toDataURL() → base64 JPEG     
  │ ~50–100 KB per frame          
  └──── POST /analyze-frame/ ────►  inference.py
                                      MediaPipe FaceMesh (CPU)
                                      EAR / gaze / head_yaw math
                                      Keras ensemble prediction
                                      Save EngagementRecord to DB
  ◄─── JSON { label, conf } ─────┘
  │
  Update UI
```

### After (Target — Client-Side)

```
Browser                           Django Server
───────────────────────────────   ─────────────────
📹 Webcam
  │
  ▼
MediaPipe WASM (WebGL GPU)  ← runs locally, ~5ms
  │ 478 facial landmarks
  ▼
JS: EAR / gaze / head_yaw   ← trivial math, ~0.1ms
  │
  ▼
TensorFlow.js model         ← runs locally, ~10ms
  │ label + probabilities
  ▼
Update UI immediately       ← zero network latency
  │
  └──── POST /save-record/ ──────►  views.py
         ~200 bytes JSON              Save EngagementRecord to DB
                              ◄─────  { status: 'ok' }
```

---

## Step 1: Convert Keras Models to TensorFlow.js Format

This is a one-time offline step done on your development machine.

### 1.1 Install the converter

```bash
pip install tensorflowjs
```

### 1.2 Convert each model

Your models are in `ml_engine/saved_models/`. Run this for each `.keras` file:

```bash
tensorflowjs_converter \
    --input_format=keras \
    ml_engine/saved_models/your_model.keras \
    static/js/models/your_model/
```

This produces a `model.json` + several `group1-shard*.bin` weight files.

### 1.3 Recommended output structure

```
engagement_project/
└── static/
    └── js/
        └── models/
            ├── estimator_0/
            │   ├── model.json
            │   └── group1-shard1of1.bin
            ├── estimator_1/
            │   ├── model.json
            │   └── group1-shard1of1.bin
            └── scaler.json        ← see Step 1.4
```

### 1.4 Export the scaler parameters

The Python `StandardScaler` must be replicated in JS. Export its parameters:

```python
# Run this once in a Python script
import joblib, json

scaler = joblib.load('ml_engine/saved_models/scaler.pkl')
export = {
    'mean': scaler.mean_.tolist(),
    'scale': scaler.scale_.tolist()
}
with open('static/js/models/scaler.json', 'w') as f:
    json.dump(export, f)
```

---

## Step 2: Add Client-Side Libraries

Add these CDN scripts to `templates/sessions_app/live_monitor.html` inside `{% block extra_js %}`, **before** your existing script:

```html
<!-- MediaPipe Tasks Vision (Face Landmark Detection) -->
<script src="https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/vision_bundle.js" crossorigin="anonymous"></script>

<!-- TensorFlow.js with WebGL backend -->
<script src="https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.15.0/dist/tf.min.js"></script>
```

> **Note:** The MediaPipe bundle is ~3 MB and TF.js is ~2 MB. Both are cached after the first load. Consider self-hosting these in `static/` for an offline/LAN deployment.

---

## Step 3: Rewrite `inference.py` Logic in JavaScript

Create a new file: `static/js/engagement_inference.js`

```javascript
// ═══════════════════════════════════════════════════════════
//  ThirdEyeAI — Client-Side Engagement Inference Engine
//  Mirrors logic from ml_engine/inference.py
// ═══════════════════════════════════════════════════════════

const LABEL_MAP = ['very_low', 'low', 'high', 'very_high'];

// Landmark indices (must match inference.py exactly)
const LEFT_EYE   = [362, 385, 387, 263, 373, 380];
const RIGHT_EYE  = [33,  160, 158, 133, 153, 144];
const LEFT_IRIS  = [474, 475, 476, 477];
const RIGHT_IRIS = [469, 470, 471, 472];
const NOSE_TIP   = 1;
const CHIN       = 152;
const FOREHEAD   = 10;
const MOUTH_L    = 61;
const MOUTH_R    = 291;
const FACE_L     = 234;
const FACE_R     = 454;

// EAR thresholds (must match inference.py)
const EAR_OPEN   = 0.20;
const EAR_HALF   = 0.14;
const EAR_CLOSED = 0.10;

let scoreHistory = [];
const HISTORY_LEN = 3;

// ── Utility ────────────────────────────────────────────────

function norm(a, b) {
    return Math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2);
}

function lmPt(landmarks, idx) {
    // MediaPipe JS returns landmarks as {x, y, z} normalized (0–1)
    return [landmarks[idx].x, landmarks[idx].y];
}

// ── Eye Aspect Ratio ───────────────────────────────────────

function earValue(landmarks, indices) {
    try {
        const pts = indices.map(i => lmPt(landmarks, i));
        const v1 = norm(pts[1], pts[5]);
        const v2 = norm(pts[2], pts[4]);
        const h  = norm(pts[0], pts[3]);
        return (v1 + v2) / (2.0 * h + 1e-6);
    } catch {
        return 0.20;
    }
}

// ── Engagement Score Computation ───────────────────────────

function computeEngagement(landmarks) {
    const earL   = earValue(landmarks, LEFT_EYE);
    const earR   = earValue(landmarks, RIGHT_EYE);
    const earAvg = (earL + earR) / 2.0;

    // Hard gate: eyes closed
    if (earAvg < EAR_CLOSED) {
        return { score: 0.05, eyeGate: 'closed', numEyes: 0, earAvg };
    }

    let eyeScore, maxScore;
    if (earAvg < EAR_HALF) {
        eyeScore = Math.min((earAvg - EAR_CLOSED) / (EAR_HALF - EAR_CLOSED), 0.35);
        maxScore = 0.40;
    } else if (earAvg < EAR_OPEN) {
        eyeScore = Math.min((earAvg - EAR_HALF) / (EAR_OPEN - EAR_HALF) * 0.7 + 0.30, 1.0);
        maxScore = 0.65;
    } else {
        eyeScore = Math.min((earAvg - EAR_OPEN) / 0.15 * 0.3 + 0.70, 1.0);
        maxScore = 1.0;
    }

    // Gaze score
    let gazeScore = 0.55;
    try {
        const ixL = LEFT_IRIS.reduce((s, i) => s + landmarks[i].x, 0) / LEFT_IRIS.length;
        const exL = LEFT_EYE.reduce((s, i) => s + landmarks[i].x, 0)  / LEFT_EYE.length;
        const iyL = LEFT_IRIS.reduce((s, i) => s + landmarks[i].y, 0) / LEFT_IRIS.length;
        const eyL = LEFT_EYE.reduce((s, i) => s + landmarks[i].y, 0)  / LEFT_EYE.length;
        const ixR = RIGHT_IRIS.reduce((s, i) => s + landmarks[i].x, 0)/ RIGHT_IRIS.length;
        const exR = RIGHT_EYE.reduce((s, i) => s + landmarks[i].x, 0) / RIGHT_EYE.length;
        const off = Math.abs(ixL-exL) + Math.abs(iyL-eyL) + Math.abs(ixR-exR);
        gazeScore = Math.max(0, Math.min(1.0 - off * 18, 1.0));
    } catch {}

    // Head yaw
    let headScore = 0.7;
    try {
        const noseX   = landmarks[NOSE_TIP].x;
        const centerX = (landmarks[FACE_L].x + landmarks[FACE_R].x) / 2.0;
        headScore = Math.max(0, Math.min(1.0 - Math.abs(noseX - centerX) * 9, 1.0));
    } catch {}

    // Face position
    let centS = 0.5, sizeS = 0.4;
    try {
        const fx   = (landmarks[FACE_L].x + landmarks[FACE_R].x) / 2.0;
        const fy   = (landmarks[FOREHEAD].y + landmarks[CHIN].y)  / 2.0;
        centS = Math.max(0, Math.min(1.0 - Math.abs(fx-0.5)*2.5 - Math.abs(fy-0.5)*1.5, 1.0));
        const fw  = Math.abs(landmarks[FACE_L].x - landmarks[FACE_R].x);
        const fh  = Math.abs(landmarks[CHIN].y   - landmarks[FOREHEAD].y);
        sizeS = Math.max(0, Math.min(fw * fh * 8, 1.0));
    } catch {}

    // Weighted score (weights must match inference.py)
    const raw = 0.40*eyeScore + 0.22*gazeScore + 0.15*headScore + 0.13*centS + 0.07*sizeS + 0.03;
    return {
        score:    Math.min(raw, maxScore),
        eyeGate:  earAvg >= EAR_OPEN ? 'open' : 'half',
        numEyes:  earAvg >= EAR_OPEN ? 2 : (earAvg >= EAR_HALF ? 1 : 0),
        earAvg,
        centS,
        faceCentered: centS > 0.5
    };
}

// ── Smoothing & Label ──────────────────────────────────────

function smoothLabel(rawScore) {
    scoreHistory.push(rawScore);
    if (scoreHistory.length > HISTORY_LEN) scoreHistory.shift();
    const score = scoreHistory.reduce((a, b) => a + b, 0) / scoreHistory.length;

    let label, base;
    if      (score < 0.20) { label = 0; base = [0.75, 0.17, 0.06, 0.02]; }
    else if (score < 0.42) { label = 1; base = [0.07, 0.68, 0.20, 0.05]; }
    else if (score < 0.65) { label = 2; base = [0.04, 0.11, 0.70, 0.15]; }
    else                   { label = 3; base = [0.02, 0.05, 0.18, 0.75]; }

    // Small noise for probability variation
    const probs = base.map(p => Math.max(0, p + (Math.random() - 0.5) * 0.03));
    const sum   = probs.reduce((a, b) => a + b, 0);
    const norm  = probs.map(p => p / sum);

    return {
        label:  LABEL_MAP[label],
        probs:  { very_low: norm[0], low: norm[1], high: norm[2], very_high: norm[3] },
        confidence: Math.max(...norm),
        score
    };
}

// ── Public API ─────────────────────────────────────────────

/**
 * Main inference function — call with a MediaPipe face landmarks result.
 * @param {Array} landmarks  — array of 478 {x, y, z} objects from MediaPipe
 * @returns {Object}         — { label, confidence, probabilities, face_stats }
 */
function predictFromLandmarks(landmarks) {
    if (!landmarks || landmarks.length === 0) {
        return {
            label: 'very_low',
            confidence: 0.90,
            model: 'client_mediapipe',
            probabilities: { very_low: 0.90, low: 0.07, high: 0.02, very_high: 0.01 },
            face_stats: { face_detected: false, eyes_detected: 0, face_centered: false }
        };
    }

    const eng = computeEngagement(landmarks);
    const out = smoothLabel(eng.score);

    return {
        label:      out.label,
        confidence: parseFloat(out.confidence.toFixed(4)),
        model:      'client_mediapipe',
        probabilities: {
            very_low:  parseFloat(out.probs.very_low.toFixed(4)),
            low:       parseFloat(out.probs.low.toFixed(4)),
            high:      parseFloat(out.probs.high.toFixed(4)),
            very_high: parseFloat(out.probs.very_high.toFixed(4)),
        },
        face_stats: {
            face_detected: true,
            eyes_detected: eng.numEyes,
            face_centered: eng.faceCentered,
            score:    parseFloat(eng.score.toFixed(3)),
            ear_avg:  parseFloat(eng.earAvg.toFixed(3)),
        }
    };
}
```

---

## Step 4: Rewrite the Live Monitor Loop

Replace the `captureAndAnalyze()` function in `live_monitor.html` with this client-side version.

### 4.1 Initialise MediaPipe on page load

```javascript
import { FaceLandmarker, FilesetResolver } from 
    'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/vision_bundle.js';

let faceLandmarker = null;

async function initMediaPipe() {
    const vision = await FilesetResolver.forVisionTasks(
        'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
    );
    faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
        baseOptions: {
            modelAssetPath:
                'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task',
            delegate: 'GPU'   // falls back to CPU automatically
        },
        runningMode:          'VIDEO',
        numFaces:             1,
        minFaceDetectionConfidence: 0.5,
        minTrackingConfidence:      0.5,
        outputFaceBlendshapes:      false,
        outputFacialTransformationMatrixes: false
    });
    console.log('MediaPipe FaceLandmarker ready');
}

// Call once on page load
initMediaPipe();
```

### 4.2 Replace `captureAndAnalyze()`

```javascript
async function captureAndAnalyze() {
    const video = document.getElementById('webcam');
    if (!video.srcObject || !faceLandmarker) return;

    // Run MediaPipe locally — no canvas, no base64, no network
    const result = faceLandmarker.detectForVideo(video, performance.now());

    let prediction;
    if (result.faceLandmarks && result.faceLandmarks.length > 0) {
        // Face found — run JS inference
        prediction = predictFromLandmarks(result.faceLandmarks[0]);
    } else {
        // No face — return very_low
        prediction = predictFromLandmarks(null);
    }

    // Update UI immediately (same as before)
    updateUI(prediction);

    // Only send a tiny JSON to the server to save the record
    await saveRecord(prediction);
}

async function saveRecord(prediction) {
    try {
        await fetch('/sessions/save-record/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                session_id:       SESSION_ID,
                engagement_level: prediction.label,
                confidence_score: prediction.confidence,
                model_used:       prediction.model
            })
        });
    } catch (e) {
        console.warn('Save failed (offline?):', e);
        // Optionally queue and retry
    }
}
```

---

## Step 5: Add a Lightweight `save-record` Endpoint

The current `/analyze-frame/` endpoint does ML inference + DB save. You need a new endpoint that **only saves**.

### 5.1 `sessions_app/views.py` — Add new view

```python
@login_required
def save_record(request):
    """
    Lightweight endpoint: receives pre-computed engagement result from client
    and saves it to the database. No ML inference runs here.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)
    
    try:
        data       = json.loads(request.body)
        session_id = data.get('session_id')
        level      = data.get('engagement_level')
        confidence = float(data.get('confidence_score', 0.0))
        model_used = data.get('model_used', 'client_mediapipe')

        # Validate inputs
        valid_levels = ['very_low', 'low', 'high', 'very_high']
        if not session_id or level not in valid_levels:
            return JsonResponse({'status': 'error', 'message': 'Invalid data'}, status=400)

        session = get_object_or_404(LearningSession, pk=session_id)

        # Same guards as before
        if session.status != 'active':
            return JsonResponse({'status': 'error', 'message': 'Session not active'})
        if not SessionEnrollment.objects.filter(session=session, student=request.user).exists():
            return JsonResponse({'status': 'error', 'message': 'Not enrolled'})

        EngagementRecord.objects.create(
            session          = session,
            student          = request.user,
            engagement_level = level,
            confidence_score = confidence,
            model_used       = model_used
        )
        return JsonResponse({'status': 'ok'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
```

### 5.2 `sessions_app/urls.py` — Register the route

```python
from django.urls import path
from . import views

urlpatterns = [
    # ... existing routes ...
    path('save-record/', views.save_record, name='save_record'),
]
```

---

## Step 6: (Optional) TensorFlow.js Ensemble

If you want to use your trained Keras ensemble instead of the rule-based EAR/gaze scorer:

### 6.1 Load models at startup

```javascript
let tfModels = [];
let tfScaler = null;

async function loadTFModels() {
    // Load scaler parameters
    const scalerResp = await fetch('/static/js/models/scaler.json');
    tfScaler = await scalerResp.json();

    // Load each estimator
    const modelNames = ['estimator_0', 'estimator_1', 'estimator_2'];
    for (const name of modelNames) {
        const model = await tf.loadLayersModel(`/static/js/models/${name}/model.json`);
        tfModels.push(model);
    }
    console.log(`Loaded ${tfModels.length} TF.js models`);
}
```

### 6.2 Predict using the ensemble

```javascript
function applyScaler(features) {
    return features.map((v, i) => (v - tfScaler.mean[i]) / (tfScaler.scale[i] + 1e-8));
}

async function predictWithEnsemble(featureArray) {
    const scaled = applyScaler(featureArray);
    const inputTensor = tf.tensor2d([scaled]);

    const allProbs = [];
    for (const model of tfModels) {
        const pred = model.predict(inputTensor);
        const probs = await pred.data();
        allProbs.push(Array.from(probs));
        pred.dispose();
    }
    inputTensor.dispose();

    // Average ensemble probabilities
    const avgProbs = allProbs[0].map((_, i) =>
        allProbs.reduce((sum, p) => sum + p[i], 0) / allProbs.length
    );
    const labelIdx = avgProbs.indexOf(Math.max(...avgProbs));
    return { label: LABEL_MAP[labelIdx], probs: avgProbs, confidence: avgProbs[labelIdx] };
}
```

> **Note:** The feature array fed to the TF.js model must match the features used during Python training exactly. Check `ml_engine/generate_dataset.py` to confirm the feature order.

---

## Performance Expectations

| Metric | Server-Side (Current) | Client-Side (After) |
|---|---|---|
| **Network per analysis** | ~75 KB (JPEG upload + response) | ~200 bytes (JSON save only) |
| **End-to-end latency** | 300 – 800 ms | 5 – 20 ms |
| **Server CPU per user** | High (MediaPipe, NumPy) | Zero (inference is local) |
| **Max concurrent users** | ~30 (single server, Gunicorn) | Effectively unlimited |
| **Privacy** | Raw video frames sent to server | Video never leaves the device |
| **First-load overhead** | None | ~5 MB (models, cached after first load) |

---

## Migration Checklist

- [ ] `pip install tensorflowjs` and convert all `.keras` models
- [ ] Export `scaler.json` from Python
- [ ] Place converted model files in `static/js/models/`
- [ ] Add MediaPipe and TF.js `<script>` tags to `live_monitor.html`
- [ ] Create `static/js/engagement_inference.js` with JS inference logic
- [ ] Replace `captureAndAnalyze()` in `live_monitor.html`
- [ ] Add `save_record` view to `sessions_app/views.py`
- [ ] Register `save-record/` URL in `sessions_app/urls.py`
- [ ] Run `python manage.py collectstatic`
- [ ] Test with 1 user, verify DB records are saved correctly
- [ ] Test with 5+ concurrent browser tabs to verify scalability
- [ ] (Optional) Deprecate or keep `/analyze-frame/` for legacy compatibility

---

## Keeping `/analyze-frame/` as a Fallback

You can keep the existing server-side endpoint alive and add a feature flag:

```javascript
const USE_CLIENT_INFERENCE = true;  // toggle to false to revert to server-side

async function captureAndAnalyze() {
    if (USE_CLIENT_INFERENCE) {
        await captureAndAnalyzeClient();
    } else {
        await captureAndAnalyzeServer();  // existing function, unchanged
    }
}
```

This way you can A/B test or roll back instantly without breaking anything.

---

*Document authored for ThirdEyeAI — `docs/client-side-inference.md`*
