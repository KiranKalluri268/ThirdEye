# Fix sessions_app/views.py - students see ALL sessions, can join any
sessions_views = """from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import LearningSession, SessionEnrollment, EngagementRecord
import json


@login_required
def session_list(request):
    if request.user.role in ['admin', 'instructor']:
        sessions = LearningSession.objects.filter(instructor=request.user).order_by('-created_at')
    else:
        # Students see ALL available sessions
        sessions = LearningSession.objects.all().order_by('-created_at')
    return render(request, 'sessions_app/session_list.html', {'sessions': sessions})


@login_required
def create_session(request):
    if request.user.role not in ['admin', 'instructor']:
        return redirect('sessions_app:list')
    if request.method == 'POST':
        session = LearningSession.objects.create(
            title=request.POST['title'],
            description=request.POST.get('description', ''),
            instructor=request.user,
            start_time=request.POST['start_time'],
            status='scheduled'
        )
        return redirect('sessions_app:detail', pk=session.pk)
    return render(request, 'sessions_app/create_session.html')


@login_required
def session_detail(request, pk):
    session = get_object_or_404(LearningSession, pk=pk)
    enrollments = session.enrollments.select_related('student')
    records = session.engagement_records.select_related('student').order_by('-timestamp')[:50]
    is_enrolled = SessionEnrollment.objects.filter(session=session, student=request.user).exists()
    return render(request, 'sessions_app/session_detail.html', {
        'session': session,
        'enrollments': enrollments,
        'records': records,
        'is_enrolled': is_enrolled,
    })


@login_required
def join_session(request, pk):
    session = get_object_or_404(LearningSession, pk=pk)
    SessionEnrollment.objects.get_or_create(session=session, student=request.user)
    return render(request, 'sessions_app/live_monitor.html', {'session': session})


@login_required
def analyze_frame(request):
    if request.method == 'POST':
        try:
            from ml_engine.inference import predict_engagement
            data = json.loads(request.body)
            session_id = data.get('session_id')
            frame_b64 = data.get('frame')
            result = predict_engagement(frame_b64)
            session = LearningSession.objects.get(pk=session_id)
            EngagementRecord.objects.create(
                session=session,
                student=request.user,
                engagement_level=result['level'],
                confidence_score=result['confidence'],
                model_used=result['model']
            )
            return JsonResponse({'status': 'success', 'result': result})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid method'})
"""

# Fix dashboard/views.py - student dashboard shows correct data
dashboard_views = """from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from sessions_app.models import LearningSession, EngagementRecord, SessionEnrollment
from django.db.models import Count, Avg
import json


@login_required
def home(request):
    user = request.user
    if user.role in ['admin', 'instructor']:
        total_sessions = LearningSession.objects.filter(instructor=user).count()
        active_sessions = LearningSession.objects.filter(instructor=user, status='active').count()
        total_students = SessionEnrollment.objects.filter(
            session__instructor=user
        ).values('student').distinct().count()
        recent_records = EngagementRecord.objects.filter(
            session__instructor=user
        ).select_related('student', 'session').order_by('-timestamp')[:10]
        context = {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'total_students': total_students,
            'recent_records': recent_records,
            'is_instructor': True,
        }
    else:
        # Student dashboard
        total_available = LearningSession.objects.count()
        enrolled_ids = SessionEnrollment.objects.filter(student=user).values_list('session_id', flat=True)
        my_sessions = len(enrolled_ids)
        my_records = EngagementRecord.objects.filter(student=user)
        avg_confidence = my_records.aggregate(avg=Avg('confidence_score'))['avg'] or 0
        recent_records = my_records.select_related('session').order_by('-timestamp')[:10]
        level_counts = {
            'very_low': my_records.filter(engagement_level='very_low').count(),
            'low': my_records.filter(engagement_level='low').count(),
            'high': my_records.filter(engagement_level='high').count(),
            'very_high': my_records.filter(engagement_level='very_high').count(),
        }
        # Recent available sessions for student
        available_sessions = LearningSession.objects.all().order_by('-created_at')[:6]
        context = {
            'my_sessions': my_sessions,
            'total_available': total_available,
            'total_analyses': my_records.count(),
            'avg_confidence': round(avg_confidence * 100, 1),
            'recent_records': recent_records,
            'level_counts': json.dumps(level_counts),
            'available_sessions': available_sessions,
            'is_instructor': False,
        }
    return render(request, 'dashboard/home.html', context)


@login_required
def reports(request):
    user = request.user
    records = EngagementRecord.objects.filter(student=user).select_related('session').order_by('-timestamp')
    return render(request, 'dashboard/reports.html', {'records': records})
"""

# Fix dashboard/home.html - shows available sessions for students
dashboard_home = """{% extends 'base.html' %}
{% block title %}Dashboard - EngageAI{% endblock %}
{% block page_title %}Dashboard{% endblock %}
{% block content %}

<!-- Stats Row -->
<div class="row g-4 mb-4">
    {% if is_instructor %}
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">{{ total_sessions }}</div><div class="stat-label mt-1">My Sessions</div></div>
                <div class="icon" style="background:#ede9fe;color:#6366f1;"><i class="bi bi-camera-video-fill"></i></div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">{{ active_sessions }}</div><div class="stat-label mt-1">Active Sessions</div></div>
                <div class="icon" style="background:#dcfce7;color:#16a34a;"><i class="bi bi-broadcast"></i></div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">{{ total_students }}</div><div class="stat-label mt-1">Total Students</div></div>
                <div class="icon" style="background:#dbeafe;color:#2563eb;"><i class="bi bi-people-fill"></i></div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">94.25%</div><div class="stat-label mt-1">Model Accuracy</div></div>
                <div class="icon" style="background:#fef9c3;color:#d97706;"><i class="bi bi-cpu-fill"></i></div>
            </div>
        </div>
    </div>
    {% else %}
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">{{ total_available }}</div><div class="stat-label mt-1">Available Sessions</div></div>
                <div class="icon" style="background:#ede9fe;color:#6366f1;"><i class="bi bi-camera-video-fill"></i></div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">{{ my_sessions }}</div><div class="stat-label mt-1">Joined Sessions</div></div>
                <div class="icon" style="background:#dcfce7;color:#16a34a;"><i class="bi bi-check-circle-fill"></i></div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">{{ total_analyses }}</div><div class="stat-label mt-1">Analyses Done</div></div>
                <div class="icon" style="background:#dbeafe;color:#2563eb;"><i class="bi bi-activity"></i></div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">{{ avg_confidence }}%</div><div class="stat-label mt-1">Avg Confidence</div></div>
                <div class="icon" style="background:#fef9c3;color:#d97706;"><i class="bi bi-graph-up-arrow"></i></div>
            </div>
        </div>
    </div>
    {% endif %}
</div>

{% if is_instructor %}
<!-- Instructor: Recent engagement records -->
<div class="custom-table">
    <div class="p-3 border-bottom d-flex justify-content-between align-items-center">
        <h6 class="fw-bold mb-0">Recent Engagement Records</h6>
        <a href="{% url 'sessions_app:create' %}" class="btn btn-sm btn-primary">
            <i class="bi bi-plus me-1"></i>New Session
        </a>
    </div>
    <table class="table table-hover mb-0">
        <thead><tr><th>Student</th><th>Session</th><th>Level</th><th>Confidence</th><th>Time</th></tr></thead>
        <tbody>
            {% for rec in recent_records %}
            <tr>
                <td>{{ rec.student.get_full_name|default:rec.student.username }}</td>
                <td>{{ rec.session.title|truncatechars:25 }}</td>
                <td><span class="engagement-badge badge-{{ rec.engagement_level }}">{{ rec.get_engagement_level_display }}</span></td>
                <td>{{ rec.confidence_score|floatformat:2 }}</td>
                <td class="text-muted" style="font-size:0.8rem;">{{ rec.timestamp|timesince }} ago</td>
            </tr>
            {% empty %}
            <tr><td colspan="5" class="text-center text-muted py-4">
                <i class="bi bi-camera-video d-block mb-2" style="font-size:2rem;"></i>
                No engagement records yet. <a href="{% url 'sessions_app:create' %}">Create a session</a> to get started.
            </td></tr>
            {% endfor %}
        </tbody>
    </table>
</div>

{% else %}
<!-- Student: Available sessions + chart -->
<div class="row g-4">
    <div class="col-md-4">
        <div class="stat-card">
            <h6 class="fw-bold mb-3">My Engagement Distribution</h6>
            <canvas id="engagementChart" height="220"></canvas>
            {% if total_analyses == 0 %}
            <p class="text-center text-muted mt-3" style="font-size:0.8rem;">Join a session and start monitoring to see data</p>
            {% endif %}
        </div>
    </div>
    <div class="col-md-8">
        <div class="custom-table">
            <div class="p-3 border-bottom d-flex justify-content-between align-items-center">
                <h6 class="fw-bold mb-0">Available Sessions</h6>
                <a href="{% url 'sessions_app:list' %}" class="btn btn-sm btn-outline-primary">View All</a>
            </div>
            {% if available_sessions %}
            <div class="p-3">
                <div class="row g-3">
                    {% for session in available_sessions %}
                    <div class="col-md-6">
                        <div class="p-3 rounded-3 border" style="background:#f8fafc;">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <span class="badge {% if session.status == 'active' %}bg-success{% elif session.status == 'scheduled' %}bg-warning text-dark{% else %}bg-secondary{% endif %}" style="font-size:0.7rem;">
                                    {{ session.get_status_display }}
                                </span>
                                <small class="text-muted" style="font-size:0.75rem;">{{ session.start_time|date:"M d" }}</small>
                            </div>
                            <div class="fw-bold mb-1" style="font-size:0.875rem;">{{ session.title|truncatechars:30 }}</div>
                            <small class="text-muted d-block mb-2">
                                <i class="bi bi-person me-1"></i>{{ session.instructor.get_full_name|default:session.instructor.username }}
                            </small>
                            <a href="{% url 'sessions_app:join' session.pk %}" class="btn btn-primary btn-sm w-100">
                                <i class="bi bi-camera-video me-1"></i>Join & Monitor
                            </a>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
            {% else %}
            <div class="text-center py-5 text-muted">
                <i class="bi bi-camera-video d-block mb-2" style="font-size:2.5rem;"></i>
                No sessions available yet. Ask your instructor to create one.
            </div>
            {% endif %}
        </div>
    </div>
</div>

<!-- Student recent records -->
{% if recent_records %}
<div class="custom-table mt-4">
    <div class="p-3 border-bottom d-flex justify-content-between align-items-center">
        <h6 class="fw-bold mb-0">My Recent Engagement Records</h6>
        <a href="{% url 'dashboard:reports' %}" class="btn btn-sm btn-outline-primary">View All</a>
    </div>
    <table class="table table-hover mb-0">
        <thead><tr><th>Session</th><th>Level</th><th>Confidence</th><th>Time</th></tr></thead>
        <tbody>
            {% for rec in recent_records %}
            <tr>
                <td>{{ rec.session.title|truncatechars:30 }}</td>
                <td><span class="engagement-badge badge-{{ rec.engagement_level }}">{{ rec.get_engagement_level_display }}</span></td>
                <td>{{ rec.confidence_score|floatformat:2 }}</td>
                <td class="text-muted" style="font-size:0.8rem;">{{ rec.timestamp|timesince }} ago</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endif %}
{% endif %}

{% endblock %}
{% block extra_js %}
{% if not is_instructor %}
<script>
const ctx = document.getElementById('engagementChart').getContext('2d');
const data = {{ level_counts|safe }};
new Chart(ctx, {
    type: 'doughnut',
    data: {
        labels: ['Very Low', 'Low', 'High', 'Very High'],
        datasets: [{
            data: [data.very_low, data.low, data.high, data.very_high],
            backgroundColor: ['#fee2e2','#fef9c3','#dbeafe','#dcfce7'],
            borderColor: ['#ef4444','#f59e0b','#3b82f6','#10b981'],
            borderWidth: 2
        }]
    },
    options: {
        responsive: true,
        plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } },
        cutout: '60%'
    }
});
</script>
{% endif %}
{% endblock %}"""

files = {
    'sessions_app/views.py': sessions_views,
    'dashboard/views.py': dashboard_views,
    'templates/dashboard/home.html': dashboard_home,
}

import os
for filepath, content in files.items():
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content.strip())
    print(f'✓ Written: {filepath}')

print('\nALL FILES FIXED SUCCESSFULLY!')
