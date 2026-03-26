from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('users/', views.user_management, name='users'),
    path('model-config/', views.model_config, name='model_config'),
    path('analytics/', views.analytics, name='analytics'),
]