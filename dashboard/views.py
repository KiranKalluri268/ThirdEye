from django.shortcuts import render
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