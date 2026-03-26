# accounts/urls.py
accounts_urls = """from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
]
"""

# dashboard/urls.py
dashboard_urls = """from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('reports/', views.reports, name='reports'),
]
"""

# sessions_app/urls.py
sessions_urls = """from django.urls import path
from . import views

app_name = 'sessions_app'

urlpatterns = [
    path('', views.session_list, name='list'),
    path('create/', views.create_session, name='create'),
    path('<int:pk>/', views.session_detail, name='detail'),
    path('<int:pk>/join/', views.join_session, name='join'),
    path('analyze-frame/', views.analyze_frame, name='analyze_frame'),
]
"""

# admin_panel/urls.py
admin_urls = """from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('users/', views.user_management, name='users'),
    path('model-config/', views.model_config, name='model_config'),
    path('analytics/', views.analytics, name='analytics'),
]
"""

# engagement_project/urls.py
main_urls = """from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('accounts:login'), name='home'),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('sessions/', include('sessions_app.urls')),
    path('admin-panel/', include('admin_panel.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"""

# accounts/views.py
accounts_views = """from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, LoginForm


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Welcome {user.first_name}! Account created successfully.')
        return redirect('dashboard:home')
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    form = LoginForm(request, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f'Welcome back, {user.first_name or user.username}!')
        return redirect('dashboard:home')
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.phone = request.POST.get('phone', '')
        user.bio = request.POST.get('bio', '')
        user.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html', {'user': request.user})
"""

# accounts/forms.py
accounts_forms = """from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=[('student', 'Student'), ('instructor', 'Instructor')])

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
"""

# dashboard/views.py
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
        enrolled_ids = SessionEnrollment.objects.filter(student=user).values_list('session_id', flat=True)
        my_sessions = LearningSession.objects.filter(id__in=enrolled_ids).count()
        my_records = EngagementRecord.objects.filter(student=user)
        avg_confidence = my_records.aggregate(avg=Avg('confidence_score'))['avg'] or 0
        recent_records = my_records.select_related('session').order_by('-timestamp')[:10]
        level_counts = {
            'very_low': my_records.filter(engagement_level='very_low').count(),
            'low': my_records.filter(engagement_level='low').count(),
            'high': my_records.filter(engagement_level='high').count(),
            'very_high': my_records.filter(engagement_level='very_high').count(),
        }
        context = {
            'my_sessions': my_sessions,
            'total_analyses': my_records.count(),
            'avg_confidence': round(avg_confidence * 100, 1),
            'recent_records': recent_records,
            'level_counts': json.dumps(level_counts),
            'is_instructor': False,
        }
    return render(request, 'dashboard/home.html', context)


@login_required
def reports(request):
    user = request.user
    records = EngagementRecord.objects.filter(student=user).select_related('session').order_by('-timestamp')
    return render(request, 'dashboard/reports.html', {'records': records})
"""

# admin_panel/views.py
admin_views = """from django.shortcuts import render, redirect
from django.db.models import Count, Avg
from sessions_app.models import LearningSession, EngagementRecord, SessionEnrollment
from accounts.models import CustomUser
import json
import os
from django.conf import settings


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role not in ['admin', 'instructor']:
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
    return render(request, 'admin_panel/model_config.html', {'model_files': model_files})


@admin_required
def analytics(request):
    sessions = LearningSession.objects.annotate(
        student_count=Count('enrollments', distinct=True),
        record_count=Count('engagement_records'),
        avg_confidence=Avg('engagement_records__confidence_score')
    ).order_by('-created_at')
    return render(request, 'admin_panel/analytics.html', {'sessions': sessions})
"""

# sessions_app/views.py
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
        enrolled_ids = SessionEnrollment.objects.filter(student=request.user).values_list('session_id', flat=True)
        sessions = LearningSession.objects.filter(id__in=enrolled_ids).order_by('-created_at')
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
    return render(request, 'sessions_app/session_detail.html', {
        'session': session, 'enrollments': enrollments, 'records': records
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

# Write all files
files = {
    'accounts/urls.py':              accounts_urls,
    'accounts/views.py':             accounts_views,
    'accounts/forms.py':             accounts_forms,
    'dashboard/urls.py':             dashboard_urls,
    'dashboard/views.py':            dashboard_views,
    'sessions_app/urls.py':          sessions_urls,
    'sessions_app/views.py':         sessions_views,
    'admin_panel/urls.py':           admin_urls,
    'admin_panel/views.py':          admin_views,
    'engagement_project/urls.py':    main_urls,
}

for filepath, content in files.items():
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content.strip())
    print(f'✓ Written: {filepath}')

print('\nALL FILES WRITTEN SUCCESSFULLY!')
