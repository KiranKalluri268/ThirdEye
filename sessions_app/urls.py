from django.urls import path
from . import views

app_name = 'sessions_app'

urlpatterns = [
    path('', views.session_list, name='list'),
    path('create/', views.create_session, name='create'),
    path('<int:pk>/', views.session_detail, name='detail'),
    path('<int:pk>/join/', views.join_session, name='join'),
    path('<int:pk>/start/', views.start_session, name='start'),
    path('<int:pk>/end/', views.end_session, name='end'),
    path('analyze-frame/', views.analyze_frame, name='analyze_frame'),
]