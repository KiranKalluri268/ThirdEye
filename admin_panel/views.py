from django.shortcuts import render, redirect
from django.db.models import Count, Avg
from sessions_app.models import LearningSession, EngagementRecord, SessionEnrollment
from accounts.models import CustomUser
import json, os
from django.conf import settings


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'admin':
            return redirect('accounts:login')
        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def admin_dashboard(request):
    total_users = CustomUser.objects.filter(role='student').count()
    total_sessions = LearningSession.objects.count()
    total_analyses = EngagementRecord.objects.count()
    engagement_dist = EngagementRecord.objects.values('engagement_level').annotate(count=Count('id'))
    dist_data = {item['engagement_level']: item['count'] for item in engagement_dist}
    recent_sessions = LearningSession.objects.select_related('instructor').order_by('-created_at')[:8]
    context = {
        'total_users': total_users,
        'total_sessions': total_sessions,
        'total_analyses': total_analyses,
        'dist_data': json.dumps(dist_data),
        'recent_sessions': recent_sessions,
    }
    return render(request, 'admin_panel/dashboard.html', context)


@admin_required
def user_management(request):
    users = CustomUser.objects.all().order_by('-date_joined')
    return render(request, 'admin_panel/users.html', {'users': users})


@admin_required
def model_config(request):
    models_dir = settings.ML_MODELS_DIR
    model_files = []
    if os.path.exists(models_dir):
        model_files = [f for f in os.listdir(models_dir) if f.endswith(('.h5', '.pkl', '.keras'))]
    accuracy_bars = [
        ('Hybrid Ensemble', 94.25, '#6366f1'),
        ('ResNet Bagging', 93.75, '#3b82f6'),
        ('CNN Bagging', 93.25, '#10b981'),
        ('1D ResNet', 90.25, '#f59e0b'),
        ('1D CNN', 90.0, '#94a3b8'),
    ]
    return render(request, 'admin_panel/model_config.html', {
        'model_files': model_files,
        'accuracy_bars': accuracy_bars,
    })


@admin_required
def analytics(request):
    sessions = LearningSession.objects.annotate(
        student_count=Count('enrollments', distinct=True),
        record_count=Count('engagement_records'),
        avg_confidence=Avg('engagement_records__confidence_score')
    ).order_by('-created_at')
    return render(request, 'admin_panel/analytics.html', {'sessions': sessions})
