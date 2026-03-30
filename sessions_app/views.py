from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import LearningSession, SessionEnrollment, EngagementRecord
from accounts.models import CustomUser
import json
import logging

logger = logging.getLogger(__name__)


@login_required
def session_list(request):
    role = getattr(request.user, 'role', 'student')
    if role == 'admin':
        sessions = LearningSession.objects.all().order_by('-created_at')
    elif role == 'instructor':
        sessions = LearningSession.objects.filter(instructor=request.user).order_by('-created_at')
    else:
        # Students see all sessions they can join
        sessions = LearningSession.objects.all().order_by('-created_at')
    
    # Check for expiry on the fly for scheduled sessions
    for sess in sessions:
        sess.check_expiry()
        
    return render(request, 'sessions_app/session_list.html', {'sessions': sessions})


@login_required
def create_session(request):
    role = getattr(request.user, 'role', 'student')
    if role not in ['admin', 'instructor']:
        return redirect('sessions_app:list')
        
    instructors = None
    if role == 'admin':
        instructors = CustomUser.objects.filter(role='instructor').order_by('first_name')

    if request.method == 'POST':
        # Default instructor is current user
        session_instructor = request.user
        
        # Admin can override instructor
        if role == 'admin' and request.POST.get('instructor_id'):
            session_instructor = get_object_or_404(CustomUser, pk=request.POST['instructor_id'], role='instructor')

        # Calculate duration
        hrs  = int(request.POST.get('duration_hrs', 0))
        mins = int(request.POST.get('duration_mins', 0))
        total_mins = (hrs * 60) + mins

        session = LearningSession.objects.create(
            title=request.POST['title'],
            description=request.POST.get('description', ''),
            instructor=session_instructor,
            start_time=request.POST['start_time'],
            duration_minutes=total_mins if total_mins > 0 else 60,
            status='scheduled'
        )
        messages.success(request, f"Session '{session.title}' created successfully.")
        return redirect('sessions_app:detail', pk=session.pk)
        
    return render(request, 'sessions_app/create_session.html', {'instructors': instructors})


@login_required
def session_detail(request, pk):
    session     = get_object_or_404(LearningSession, pk=pk)
    session.check_expiry() # Update status if needed
    
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
    
    # Life cycle guard: Only active sessions can be joined
    if session.status != 'active':
        messages.error(request, f"Cannot join session '{session.title}' because it is currently {session.get_status_display().lower()}.")
        return redirect('sessions_app:detail', pk=pk)
        
    SessionEnrollment.objects.get_or_create(session=session, student=request.user)
    return render(request, 'sessions_app/live_monitor.html', {'session': session})


@login_required
def start_session(request, pk):
    session = get_object_or_404(LearningSession, pk=pk)
    session.check_expiry()
    
    # Permission check: Own instructor or admin
    if request.user != session.instructor and getattr(request.user, 'role', '') != 'admin':
        messages.error(request, "You do not have permission to start this session.")
        return redirect('sessions_app:detail', pk=pk)
        
    if session.status == 'scheduled':
        session.status = 'active'
        session.save()
        messages.success(request, f"Session '{session.title}' has been started and is now live.")
    elif session.status == 'expired':
        messages.error(request, "This session has expired and cannot be started.")
    elif session.status == 'active':
        messages.info(request, "Session is already active.")
    else:
        messages.warning(request, "Cannot start a completed session.")
        
    return redirect('sessions_app:detail', pk=pk)


@login_required
def end_session(request, pk):
    session = get_object_or_404(LearningSession, pk=pk)
    
    # Permission check: Own instructor or admin
    if request.user != session.instructor and getattr(request.user, 'role', '') != 'admin':
        messages.error(request, "You do not have permission to end this session.")
        return redirect('sessions_app:detail', pk=pk)
        
    if session.status == 'active':
        session.status = 'completed'
        session.end_time = timezone.now()
        session.save()
        messages.success(request, f"Session '{session.title}' has been ended and is now closed.")
    else:
        messages.warning(request, "Only active sessions can be ended.")
        
    return redirect('sessions_app:detail', pk=pk)


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
            
            # API Guards: Session status and user enrollment
            if session.status != 'active':
                return JsonResponse({'status': 'error', 'message': 'Session is not currently active.'})
            
            if not SessionEnrollment.objects.filter(session=session, student=request.user).exists():
                return JsonResponse({'status': 'error', 'message': 'You are not enrolled in this session.'})

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