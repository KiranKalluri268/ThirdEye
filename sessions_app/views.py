from django.shortcuts import render, redirect, get_object_or_404
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