from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from sessions_app.models import LearningSession, EngagementRecord, SessionEnrollment
from accounts.models import CustomUser
from django.db.models import Count, Avg, Case, When, Value, IntegerField
import json


@login_required
def home(request):
    user = request.user
    role = getattr(user, 'role', 'student')
    
    is_admin = role == 'admin'
    is_instructor = role == 'instructor'

    context = {
        'is_admin': is_admin,
        'is_instructor': is_instructor,
    }

    if is_admin:
        # Global stats for Admin
        context.update({
            'total_sessions': LearningSession.objects.count(),
            'active_sessions': LearningSession.objects.filter(status='active').count(),
            'total_users': CustomUser.objects.count(),
            'recent_sessions': LearningSession.objects.select_related('instructor').order_by('-created_at')[:10],
        })
    elif is_instructor:
        # Specific stats for Instructor
        total_sessions  = LearningSession.objects.filter(instructor=user).count()
        active_sessions = LearningSession.objects.filter(instructor=user, status='active').count()
        total_students  = SessionEnrollment.objects.filter(
            session__instructor=user
        ).values('student').distinct().count()
        recent_records  = EngagementRecord.objects.filter(
            session__instructor=user
        ).select_related('student', 'session').order_by('-timestamp')[:10]
        context.update({
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'total_students': total_students,
            'recent_records': recent_records,
        })
    else:
        # Specific stats for Student
        my_records      = EngagementRecord.objects.filter(student=user)
        avg_confidence  = my_records.aggregate(avg=Avg('confidence_score'))['avg'] or 0
        enrolled_ids    = SessionEnrollment.objects.filter(student=user).values_list('session_id', flat=True)
        level_counts    = {
            'very_low':  my_records.filter(engagement_level='very_low').count(),
            'low':       my_records.filter(engagement_level='low').count(),
            'high':      my_records.filter(engagement_level='high').count(),
            'very_high': my_records.filter(engagement_level='very_high').count(),
        }
        context.update({
            'my_sessions':       len(enrolled_ids),
            'total_available':   LearningSession.objects.count(),
            'total_analyses':    my_records.count(),
            'avg_confidence':    round(avg_confidence * 100, 1),
            'recent_records':    my_records.select_related('session').order_by('-timestamp')[:10],
            'level_counts':      json.dumps(level_counts),
            'available_sessions':LearningSession.objects.all().order_by('-created_at')[:6],
        })

    return render(request, 'dashboard/home.html', context)


@login_required
def reports(request):
    user = request.user
    role = getattr(user, 'role', 'student')
    is_admin = role == 'admin'
    is_instructor = role == 'instructor'
    
    session_id = request.GET.get('session_id')
    
    selected_session = None
    sessions = None
    records = None
    title = "My Reports"

    if is_admin:
        if session_id:
            # Global view for a specific session (any instructor)
            selected_session = get_object_or_404(LearningSession.objects.select_related('instructor'), id=session_id)
            records = EngagementRecord.objects.filter(session=selected_session).select_related('student').order_by('-timestamp')
            title = f"Report: {selected_session.title}"
        else:
            # Global list of all sessions for summary stats
            sessions = LearningSession.objects.select_related('instructor').all().annotate(
                student_count=Count('enrollments', distinct=True),
                avg_conf=Avg('engagement_records__confidence_score'),
                avg_level_num=Avg(
                    Case(
                        When(engagement_records__engagement_level='very_low', then=Value(1)),
                        When(engagement_records__engagement_level='low', then=Value(2)),
                        When(engagement_records__engagement_level='high', then=Value(3)),
                        When(engagement_records__engagement_level='very_high', then=Value(4)),
                        output_field=IntegerField(),
                    )
                )
            ).order_by('-created_at')
            title = "System Sessions Summary"
    elif is_instructor or is_admin: # Fallback for instructors or admins if logic allows
        if session_id:
            # Detailed view for a specific instructor session
            selected_session = get_object_or_404(LearningSession, id=session_id, instructor=user)
            records = EngagementRecord.objects.filter(session=selected_session).select_related('student').order_by('-timestamp')
            title = f"Reports: {selected_session.title}"
        else:
            # List of instructor's sessions with summary stats
            sessions = LearningSession.objects.filter(instructor=user).annotate(
                student_count=Count('enrollments', distinct=True),
                avg_conf=Avg('engagement_records__confidence_score'),
                avg_level_num=Avg(
                    Case(
                        When(engagement_records__engagement_level='very_low', then=Value(1)),
                        When(engagement_records__engagement_level='low', then=Value(2)),
                        When(engagement_records__engagement_level='high', then=Value(3)),
                        When(engagement_records__engagement_level='very_high', then=Value(4)),
                        output_field=IntegerField(),
                    )
                )
            ).order_by('-created_at')
            title = "My Sessions Summary"
    else:
        # Student view: their own records
        records = EngagementRecord.objects.filter(student=user).select_related('session').order_by('-timestamp')
        title = "My Engagement History"

    # Context construction
    context = {
        'sessions': sessions,
        'records': records,
        'selected_session': selected_session,
        'title': title,
        'is_admin': is_admin,
        'is_instructor': is_instructor,
    }

    if records:
        context['total'] = records.count()
        avg_conf_raw = records.aggregate(avg=Avg('confidence_score'))['avg'] or 0
        context['avg_confidence'] = round(avg_conf_raw * 100, 1)
    elif sessions:
        context['total'] = sessions.count()
    else:
        context['total'] = 0

    return render(request, 'dashboard/reports.html', context)