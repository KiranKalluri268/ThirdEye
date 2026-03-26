import os

# Fix 1: sessions_app/views.py — fix analyze_frame to properly save records
sessions_views = """from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import LearningSession, SessionEnrollment, EngagementRecord
import json
import logging

logger = logging.getLogger(__name__)


@login_required
def session_list(request):
    if hasattr(request.user, 'role') and request.user.role in ['admin', 'instructor']:
        sessions = LearningSession.objects.filter(instructor=request.user).order_by('-created_at')
    else:
        sessions = LearningSession.objects.all().order_by('-created_at')
    return render(request, 'sessions_app/session_list.html', {'sessions': sessions})


@login_required
def create_session(request):
    if not hasattr(request.user, 'role') or request.user.role not in ['admin', 'instructor']:
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
    session     = get_object_or_404(LearningSession, pk=pk)
    enrollments = session.enrollments.select_related('student')
    records     = session.engagement_records.select_related('student').order_by('-timestamp')[:50]
    is_enrolled = SessionEnrollment.objects.filter(session=session, student=request.user).exists()
    return render(request, 'sessions_app/session_detail.html', {
        'session': session, 'enrollments': enrollments,
        'records': records, 'is_enrolled': is_enrolled,
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
            data       = json.loads(request.body)
            session_id = data.get('session_id')
            frame_b64  = data.get('frame')

            if not session_id or not frame_b64:
                return JsonResponse({'status': 'error', 'message': 'Missing session_id or frame'})

            session = get_object_or_404(LearningSession, pk=session_id)
            result  = predict_engagement(frame_b64)

            # Save to database
            record = EngagementRecord.objects.create(
                session          = session,
                student          = request.user,
                engagement_level = result['level'],
                confidence_score = result['confidence'],
                model_used       = result.get('model', 'opencv_analyzer'),
            )

            logger.info(f"Record saved: {record.pk} | {request.user.username} | {result['level']}")

            return JsonResponse({
                'status': 'success',
                'result': result,
                'record_id': record.pk,
            })

        except Exception as e:
            logger.error(f"analyze_frame error: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid method'})
"""

# Fix 2: dashboard/views.py — show ALL records for instructor, own records for student
dashboard_views = """from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from sessions_app.models import LearningSession, EngagementRecord, SessionEnrollment
from django.db.models import Count, Avg
import json


@login_required
def home(request):
    user = request.user
    is_instructor = hasattr(user, 'role') and user.role in ['admin', 'instructor']

    if is_instructor:
        total_sessions  = LearningSession.objects.filter(instructor=user).count()
        active_sessions = LearningSession.objects.filter(instructor=user, status='active').count()
        total_students  = SessionEnrollment.objects.filter(
            session__instructor=user
        ).values('student').distinct().count()
        recent_records  = EngagementRecord.objects.filter(
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
        my_records      = EngagementRecord.objects.filter(student=user)
        avg_confidence  = my_records.aggregate(avg=Avg('confidence_score'))['avg'] or 0
        enrolled_ids    = SessionEnrollment.objects.filter(student=user).values_list('session_id', flat=True)
        level_counts    = {
            'very_low':  my_records.filter(engagement_level='very_low').count(),
            'low':       my_records.filter(engagement_level='low').count(),
            'high':      my_records.filter(engagement_level='high').count(),
            'very_high': my_records.filter(engagement_level='very_high').count(),
        }
        context = {
            'my_sessions':       len(enrolled_ids),
            'total_available':   LearningSession.objects.count(),
            'total_analyses':    my_records.count(),
            'avg_confidence':    round(avg_confidence * 100, 1),
            'recent_records':    my_records.select_related('session').order_by('-timestamp')[:10],
            'level_counts':      json.dumps(level_counts),
            'available_sessions':LearningSession.objects.all().order_by('-created_at')[:6],
            'is_instructor':     False,
        }

    return render(request, 'dashboard/home.html', context)


@login_required
def reports(request):
    user = request.user
    is_instructor = hasattr(user, 'role') and user.role in ['admin', 'instructor']

    if is_instructor:
        # Instructors see ALL records from their sessions
        records = EngagementRecord.objects.filter(
            session__instructor=user
        ).select_related('student', 'session').order_by('-timestamp')
        title = "All Student Engagement Records"
    else:
        # Students see only their own records
        records = EngagementRecord.objects.filter(
            student=user
        ).select_related('session').order_by('-timestamp')
        title = "My Engagement Reports"

    total    = records.count()
    avg_conf = records.aggregate(avg=Avg('confidence_score'))['avg'] or 0

    return render(request, 'dashboard/reports.html', {
        'records':        records,
        'title':          title,
        'total':          total,
        'avg_confidence': round(avg_conf * 100, 1),
        'is_instructor':  is_instructor,
    })
"""

# Fix 3: dashboard/reports.html — proper display
reports_html = """{% extends 'base.html' %}
{% block title %}Reports - EngageAI{% endblock %}
{% block page_title %}{{ title }}{% endblock %}
{% block content %}

<!-- Summary Stats -->
<div class="row g-4 mb-4">
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <div class="stat-value">{{ total }}</div>
                    <div class="stat-label mt-1">Total Records</div>
                </div>
                <div class="icon" style="background:#ede9fe;color:#6366f1;">
                    <i class="bi bi-activity"></i>
                </div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div>
                    <div class="stat-value">{{ avg_confidence }}%</div>
                    <div class="stat-label mt-1">Avg Confidence</div>
                </div>
                <div class="icon" style="background:#dcfce7;color:#16a34a;">
                    <i class="bi bi-graph-up"></i>
                </div>
            </div>
        </div>
    </div>
</div>

<!-- Records Table -->
<div class="custom-table">
    <div class="p-3 border-bottom d-flex justify-content-between align-items-center">
        <h6 class="fw-bold mb-0">{{ title }}</h6>
        <span class="text-muted" style="font-size:0.85rem;">{{ total }} record{{ total|pluralize }}</span>
    </div>
    <div class="table-responsive">
    <table class="table table-hover mb-0">
        <thead>
            <tr>
                <th>Session</th>
                {% if is_instructor %}<th>Student</th>{% endif %}
                <th>Level</th>
                <th>Confidence</th>
                <th>Model</th>
                <th>Date & Time</th>
            </tr>
        </thead>
        <tbody>
            {% for rec in records %}
            <tr>
                <td class="fw-medium">{{ rec.session.title|truncatechars:30 }}</td>
                {% if is_instructor %}
                <td>{{ rec.student.get_full_name|default:rec.student.username }}</td>
                {% endif %}
                <td>
                    <span class="engagement-badge badge-{{ rec.engagement_level }}">
                        {{ rec.get_engagement_level_display }}
                    </span>
                </td>
                <td>
                    <div class="d-flex align-items-center gap-2">
                        <div class="progress flex-grow-1" style="height:6px;width:80px;">
                            <div class="progress-bar"
                                 style="width:{{ rec.confidence_score_pct }}%;background:#6366f1;">
                            </div>
                        </div>
                        <span style="font-size:0.8rem;">
                            {% widthratio rec.confidence_score 1 100 %}%
                        </span>
                    </div>
                </td>
                <td>
                    <span class="badge bg-light text-dark" style="font-size:0.75rem;">
                        {{ rec.model_used|default:"opencv" }}
                    </span>
                </td>
                <td class="text-muted" style="font-size:0.82rem;">
                    {{ rec.timestamp|date:"d M Y" }}<br>
                    <small>{{ rec.timestamp|time:"H:i:s" }}</small>
                </td>
            </tr>
            {% empty %}
            <tr>
                <td colspan="6" class="text-center py-5 text-muted">
                    <i class="bi bi-camera-video d-block mb-2" style="font-size:2.5rem;"></i>
                    <strong>No records yet</strong><br>
                    <small>
                        {% if is_instructor %}
                        No students have joined your sessions yet.
                        {% else %}
                        Join a session and start camera monitoring to see records here.
                        {% endif %}
                    </small>
                    <br><br>
                    <a href="{% url 'sessions_app:list' %}" class="btn btn-primary btn-sm">
                        <i class="bi bi-camera-video me-1"></i>Go to Sessions
                    </a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    </div>
</div>
{% endblock %}"""

# Write all files
os.makedirs('templates/dashboard', exist_ok=True)

views_path = None
for candidate in ['sessions_app/views.py']:
    if os.path.exists('sessions_app'):
        views_path = candidate
        break

if views_path:
    with open('sessions_app/views.py', 'w', encoding='utf-8') as f:
        f.write(sessions_views.strip())
    print('SUCCESS - sessions_app/views.py updated')

# Find dashboard views
for candidate in ['dashboard/views.py']:
    if os.path.exists('dashboard'):
        with open('dashboard/views.py', 'w', encoding='utf-8') as f:
            f.write(dashboard_views.strip())
        print('SUCCESS - dashboard/views.py updated')
        break

with open('templates/dashboard/reports.html', 'w', encoding='utf-8') as f:
    f.write(reports_html.strip())
print('SUCCESS - templates/dashboard/reports.html updated')
print('\nAll fixes applied!')
