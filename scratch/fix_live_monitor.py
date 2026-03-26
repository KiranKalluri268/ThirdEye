import os

content = """{% extends 'base.html' %}
{% block title %}Live Monitor - EngageAI{% endblock %}
{% block page_title %}Live Session: {{ session.title }}{% endblock %}
{% block content %}
<div class="row g-4">
    <!-- Camera Feed -->
    <div class="col-md-7">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="fw-bold mb-0"><i class="bi bi-camera-video text-primary me-2"></i>Camera Feed</h6>
                <span id="status-badge" class="badge bg-secondary px-3 py-2">Stopped</span>
            </div>
            <div style="background:#0f172a;border-radius:12px;overflow:hidden;position:relative;">
                <video id="webcam" autoplay muted playsinline
                       style="width:100%;max-height:380px;object-fit:cover;display:block;"></video>
                <!-- Overlay showing live engagement on video -->
                <div id="video-overlay" style="display:none;position:absolute;top:12px;left:12px;
                     background:rgba(0,0,0,0.65);border-radius:10px;padding:8px 14px;color:#fff;">
                    <div style="font-size:0.7rem;opacity:0.7;">ENGAGEMENT</div>
                    <div id="overlay-level" style="font-size:1.2rem;font-weight:700;">--</div>
                    <div id="overlay-conf" style="font-size:0.75rem;opacity:0.8;">--</div>
                </div>
                <!-- Face detection indicator -->
                <div id="face-indicator" style="display:none;position:absolute;top:12px;right:12px;
                     background:rgba(0,0,0,0.65);border-radius:10px;padding:6px 10px;color:#fff;font-size:0.75rem;">
                    <span id="face-icon">👤</span> <span id="face-text">Detecting...</span>
                </div>
            </div>
            <div class="d-flex gap-2 mt-3 align-items-center">
                <button id="startBtn" class="btn btn-primary px-4" onclick="startMonitoring()">
                    <i class="bi bi-play-fill me-1"></i>Start Monitoring
                </button>
                <button id="stopBtn" class="btn btn-outline-danger px-4 d-none" onclick="stopMonitoring()">
                    <i class="bi bi-stop-fill me-1"></i>Stop
                </button>
                <span id="timer-display" class="text-muted ms-2" style="font-size:0.85rem;display:none;">
                    <i class="bi bi-clock me-1"></i><span id="timer-text">00:00</span>
                </span>
            </div>
        </div>
    </div>

    <!-- Right Panel -->
    <div class="col-md-5">
        <!-- Current Engagement Card -->
        <div class="stat-card mb-4">
            <h6 class="fw-bold mb-3">Current Engagement</h6>
            <div class="text-center">
                <div id="engagement-icon" style="font-size:3rem;margin-bottom:0.5rem;">😐</div>
                <div id="engagement-level"
                     style="font-size:1.8rem;font-weight:800;color:#6366f1;min-height:2.5rem;">
                    Waiting...
                </div>
                <div id="engagement-conf" class="text-muted mt-1" style="font-size:0.875rem;">
                    Start monitoring to begin
                </div>
                <!-- Confidence bar -->
                <div class="mt-3 px-2">
                    <div class="d-flex justify-content-between mb-1" style="font-size:0.75rem;">
                        <span class="text-muted">Confidence</span>
                        <span id="conf-pct" class="fw-bold">0%</span>
                    </div>
                    <div class="progress" style="height:8px;border-radius:4px;">
                        <div id="conf-bar" class="progress-bar"
                             style="width:0%;background:linear-gradient(90deg,#6366f1,#0ea5e9);transition:width 0.5s;"></div>
                    </div>
                </div>
            </div>
            <!-- Probability chart -->
            <div class="mt-3">
                <canvas id="probChart" height="140"></canvas>
            </div>
        </div>

        <!-- Face Detection Status -->
        <div class="stat-card mb-4" id="face-stats-card" style="display:none;">
            <h6 class="fw-bold mb-3">Detection Details</h6>
            <div class="row g-2 text-center">
                <div class="col-4">
                    <div id="face-det-icon" style="font-size:1.5rem;">❓</div>
                    <div style="font-size:0.7rem;color:#64748b;">Face</div>
                </div>
                <div class="col-4">
                    <div id="eyes-det-icon" style="font-size:1.5rem;">❓</div>
                    <div style="font-size:0.7rem;color:#64748b;">Eyes</div>
                </div>
                <div class="col-4">
                    <div id="center-det-icon" style="font-size:1.5rem;">❓</div>
                    <div style="font-size:0.7rem;color:#64748b;">Centered</div>
                </div>
            </div>
        </div>

        <!-- Session Info -->
        <div class="stat-card">
            <h6 class="fw-bold mb-3">Session Info</h6>
            <div class="d-flex justify-content-between mb-2" style="font-size:0.875rem;">
                <span class="text-muted">Session</span>
                <span class="fw-bold">{{ session.title|truncatechars:20 }}</span>
            </div>
            <div class="d-flex justify-content-between mb-2" style="font-size:0.875rem;">
                <span class="text-muted">Analyses Done</span>
                <span class="fw-bold text-primary" id="analysis-count">0</span>
            </div>
            <div class="d-flex justify-content-between mb-2" style="font-size:0.875rem;">
                <span class="text-muted">Model</span>
                <span class="fw-bold" id="model-used">Hybrid Ensemble</span>
            </div>
            <div class="d-flex justify-content-between" style="font-size:0.875rem;">
                <span class="text-muted">Interval</span>
                <span class="fw-bold">Every 3 seconds</span>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
let stream = null, intervalId = null, timerIntervalId = null;
let analysisCount = 0, probChart = null, secondsElapsed = 0;
const SESSION_ID = {{ session.id }};

const ICONS = {
    very_low: '😴', low: '😑', high: '🙂', very_high: '😊'
};
const COLORS = {
    very_low: '#ef4444', low: '#f59e0b', high: '#3b82f6', very_high: '#10b981'
};
const LABELS = {
    very_low: 'Very Low', low: 'Low', high: 'High', very_high: 'Very High'
};

function initChart() {
    const ctx = document.getElementById('probChart').getContext('2d');
    if (probChart) probChart.destroy();
    probChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Very Low', 'Low', 'High', 'Very High'],
            datasets: [{
                data: [0.25, 0.25, 0.25, 0.25],
                backgroundColor: ['rgba(239,68,68,0.2)', 'rgba(245,158,11,0.2)',
                                   'rgba(59,130,246,0.2)', 'rgba(16,185,129,0.2)'],
                borderColor: ['#ef4444', '#f59e0b', '#3b82f6', '#10b981'],
                borderWidth: 2, borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            animation: { duration: 500 },
            scales: {
                y: { max: 1, beginAtZero: true, ticks: { font: { size: 10 } } },
                x: { ticks: { font: { size: 10 } } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

function updateTimer() {
    secondsElapsed++;
    const m = String(Math.floor(secondsElapsed / 60)).padStart(2, '0');
    const s = String(secondsElapsed % 60).padStart(2, '0');
    document.getElementById('timer-text').textContent = m + ':' + s;
}

async function startMonitoring() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
        document.getElementById('webcam').srcObject = stream;
        document.getElementById('startBtn').classList.add('d-none');
        document.getElementById('stopBtn').classList.remove('d-none');
        document.getElementById('status-badge').className = 'badge bg-success px-3 py-2';
        document.getElementById('status-badge').textContent = '🔴 Live';
        document.getElementById('video-overlay').style.display = 'block';
        document.getElementById('face-indicator').style.display = 'block';
        document.getElementById('face-stats-card').style.display = 'block';
        document.getElementById('timer-display').style.display = 'inline';
        document.getElementById('engagement-level').textContent = 'Analyzing...';
        initChart();
        intervalId = setInterval(captureAndAnalyze, 3000);
        timerIntervalId = setInterval(updateTimer, 1000);
        // First analysis immediately
        setTimeout(captureAndAnalyze, 800);
    } catch (e) {
        alert('Camera access denied: ' + e.message);
    }
}

function stopMonitoring() {
    if (stream) stream.getTracks().forEach(t => t.stop());
    clearInterval(intervalId);
    clearInterval(timerIntervalId);
    document.getElementById('startBtn').classList.remove('d-none');
    document.getElementById('stopBtn').classList.add('d-none');
    document.getElementById('status-badge').className = 'badge bg-secondary px-3 py-2';
    document.getElementById('status-badge').textContent = 'Stopped';
    document.getElementById('video-overlay').style.display = 'none';
    document.getElementById('face-indicator').style.display = 'none';
    document.getElementById('engagement-level').textContent = 'Stopped';
}

function captureAndAnalyze() {
    const video = document.getElementById('webcam');
    if (!video.srcObject) return;
    const canvas = document.createElement('canvas');
    canvas.width = 320; canvas.height = 240;
    canvas.getContext('2d').drawImage(video, 0, 0, 320, 240);
    const frameData = canvas.toDataURL('image/jpeg', 0.75);

    fetch('/sessions/analyze-frame/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ session_id: SESSION_ID, frame: frameData })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            const r = data.result;
            const level = r.level;
            const conf  = r.confidence;
            const probs = r.probabilities;
            const color = COLORS[level];

            // Update main label
            document.getElementById('engagement-level').textContent  = LABELS[level];
            document.getElementById('engagement-level').style.color  = color;
            document.getElementById('engagement-icon').textContent   = ICONS[level];
            document.getElementById('engagement-conf').textContent   = 'Confidence: ' + (conf * 100).toFixed(1) + '%';

            // Confidence bar
            const pct = Math.round(conf * 100);
            document.getElementById('conf-bar').style.width = pct + '%';
            document.getElementById('conf-pct').textContent = pct + '%';

            // Video overlay
            document.getElementById('overlay-level').textContent = LABELS[level];
            document.getElementById('overlay-conf').textContent  = (conf * 100).toFixed(1) + '%';

            // Update chart
            if (probChart) {
                probChart.data.datasets[0].data = [
                    probs.very_low, probs.low, probs.high, probs.very_high
                ];
                probChart.update();
            }

            // Face stats
            if (r.face_stats) {
                const fs = r.face_stats;
                document.getElementById('face-det-icon').textContent  = fs.face_detected ? '✅' : '❌';
                document.getElementById('eyes-det-icon').textContent  = fs.eyes_detected >= 2 ? '✅' : fs.eyes_detected === 1 ? '⚠️' : '❌';
                document.getElementById('center-det-icon').textContent= fs.face_centered  ? '✅' : '⚠️';
                document.getElementById('face-text').textContent      = fs.face_detected  ? 'Face Detected' : 'No Face';
                document.getElementById('face-icon').textContent      = fs.face_detected  ? '✅' : '❌';
            }

            // Model used
            document.getElementById('model-used').textContent = r.model === 'hybrid_ensemble'
                ? 'Hybrid Ensemble' : 'OpenCV Analyzer';

            // Count
            analysisCount++;
            document.getElementById('analysis-count').textContent = analysisCount;
        } else {
            console.error('Analysis error:', data.message);
        }
    })
    .catch(e => console.error('Fetch error:', e));
}

function getCookie(name) {
    const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
    return v ? v[2] : null;
}
</script>
{% endblock %}"""

os.makedirs('templates/sessions_app', exist_ok=True)
with open('templates/sessions_app/live_monitor.html', 'w', encoding='utf-8') as f:
    f.write(content.strip())
print('SUCCESS - live_monitor.html written')
