import os

templates = {}

# ── base.html ───────────────────────────────────────────
templates['templates/base.html'] = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}EngageAI{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --sidebar-width: 260px;
        }
        * { font-family: 'Inter', sans-serif; }
        body { background: #f8fafc; color: #334155; }
        .sidebar {
            width: var(--sidebar-width);
            background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh;
            position: fixed;
            top: 0; left: 0;
            z-index: 1000;
            overflow-y: auto;
        }
        .sidebar .logo { padding: 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.1); }
        .sidebar .logo h5 { color: #fff; font-weight: 700; margin: 0; font-size: 1.1rem; }
        .sidebar .logo span { color: var(--primary); }
        .sidebar .nav-link {
            color: #94a3b8;
            padding: 0.65rem 1.5rem;
            border-radius: 8px;
            margin: 2px 12px;
            font-size: 0.875rem;
            font-weight: 500;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .sidebar .nav-link:hover, .sidebar .nav-link.active {
            background: rgba(99,102,241,0.2);
            color: #fff;
        }
        .sidebar .nav-link i { font-size: 1rem; width: 20px; }
        .sidebar-section-title {
            color: #475569;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            padding: 1rem 1.5rem 0.3rem;
        }
        .main-content { margin-left: var(--sidebar-width); min-height: 100vh; }
        .topbar {
            background: #fff;
            border-bottom: 1px solid #e2e8f0;
            padding: 0.85rem 1.5rem;
            position: sticky;
            top: 0;
            z-index: 999;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .topbar .page-title { font-size: 1.1rem; font-weight: 600; color: #0f172a; margin: 0; }
        .content-area { padding: 2rem 1.5rem; }
        .stat-card {
            background: #fff;
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid #e2e8f0;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .stat-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,0.08); }
        .stat-card .icon {
            width: 52px; height: 52px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
        }
        .stat-card .stat-value { font-size: 2rem; font-weight: 700; color: #0f172a; line-height: 1; }
        .stat-card .stat-label { font-size: 0.8rem; color: #64748b; font-weight: 500; }
        .custom-table { background: #fff; border-radius: 16px; overflow: hidden; border: 1px solid #e2e8f0; }
        .custom-table table { margin: 0; }
        .custom-table th { background: #f8fafc; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; border-bottom: 1px solid #e2e8f0; padding: 0.85rem 1rem; }
        .custom-table td { font-size: 0.875rem; vertical-align: middle; border-color: #f1f5f9; padding: 0.75rem 1rem; }
        .engagement-badge { padding: 0.35rem 0.75rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
        .badge-very_high { background: #dcfce7; color: #15803d; }
        .badge-high { background: #dbeafe; color: #1d4ed8; }
        .badge-low { background: #fef9c3; color: #a16207; }
        .badge-very_low { background: #fee2e2; color: #b91c1c; }
        .form-control, .form-select { border-radius: 10px; border: 1.5px solid #e2e8f0; padding: 0.6rem 1rem; font-size: 0.875rem; }
        .form-control:focus, .form-select:focus { border-color: var(--primary); box-shadow: 0 0 0 3px rgba(99,102,241,0.1); }
        .btn-primary { background: var(--primary); border-color: var(--primary); border-radius: 10px; font-weight: 600; padding: 0.6rem 1.4rem; }
        .btn-primary:hover { background: var(--primary-dark); border-color: var(--primary-dark); }
        .auth-card { background: #fff; border-radius: 20px; border: 1px solid #e2e8f0; box-shadow: 0 20px 60px rgba(0,0,0,0.08); }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #f1f5f9; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
    </style>
    {% block extra_css %}{% endblock %}
</head>
<body>
{% if user.is_authenticated %}
<div class="sidebar">
    <div class="logo">
        <h5><i class="bi bi-cpu-fill" style="color:var(--primary)"></i> Engage<span>AI</span></h5>
        <small style="color:#64748b;font-size:0.75rem;">Student Engagement Detection</small>
    </div>
    <nav class="mt-3">
        <div class="sidebar-section-title">Main</div>
        <a href="{% url 'dashboard:home' %}" class="nav-link {% if request.resolver_match.app_name == 'dashboard' %}active{% endif %}">
            <i class="bi bi-grid-1x2-fill"></i> Dashboard
        </a>
        <a href="{% url 'sessions_app:list' %}" class="nav-link {% if request.resolver_match.app_name == 'sessions_app' %}active{% endif %}">
            <i class="bi bi-camera-video-fill"></i> Sessions
        </a>
        <a href="{% url 'dashboard:reports' %}" class="nav-link">
            <i class="bi bi-bar-chart-fill"></i> My Reports
        </a>
        {% if user.role == 'admin' or user.role == 'instructor' %}
        <div class="sidebar-section-title">Admin</div>
        <a href="{% url 'admin_panel:dashboard' %}" class="nav-link {% if request.resolver_match.app_name == 'admin_panel' %}active{% endif %}">
            <i class="bi bi-speedometer2"></i> Control Panel
        </a>
        <a href="{% url 'admin_panel:users' %}" class="nav-link">
            <i class="bi bi-people-fill"></i> User Management
        </a>
        <a href="{% url 'admin_panel:analytics' %}" class="nav-link">
            <i class="bi bi-graph-up"></i> Analytics
        </a>
        <a href="{% url 'admin_panel:model_config' %}" class="nav-link">
            <i class="bi bi-gear-fill"></i> Model Config
        </a>
        {% endif %}
        <div class="sidebar-section-title">Account</div>
        <a href="{% url 'accounts:profile' %}" class="nav-link">
            <i class="bi bi-person-fill"></i> Profile
        </a>
        <a href="{% url 'accounts:logout' %}" class="nav-link">
            <i class="bi bi-box-arrow-right"></i> Logout
        </a>
    </nav>
</div>
<div class="main-content">
    <div class="topbar">
        <h6 class="page-title">{% block page_title %}Dashboard{% endblock %}</h6>
        <div class="d-flex align-items-center gap-3">
            <span class="badge bg-light text-dark border">{{ user.role|capfirst }}</span>
            <div class="d-flex align-items-center gap-2">
                <div style="width:32px;height:32px;border-radius:50%;background:var(--primary);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:600;font-size:0.8rem;">
                    {{ user.first_name|first|default:user.username|first|upper }}
                </div>
                <span style="font-size:0.875rem;font-weight:500;">{{ user.get_full_name|default:user.username }}</span>
            </div>
        </div>
    </div>
    <div class="content-area">
        {% if messages %}
        {% for message in messages %}
        <div class="alert alert-info alert-dismissible fade show" role="alert">
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        {% endfor %}
        {% endif %}
        {% block content %}{% endblock %}
    </div>
</div>
{% else %}
{% block auth_content %}{% endblock %}
{% endif %}
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
{% block extra_js %}{% endblock %}
</body>
</html>"""

# ── accounts/login.html ─────────────────────────────────
templates['templates/accounts/login.html'] = """{% extends 'base.html' %}
{% block title %}Login - EngageAI{% endblock %}
{% block auth_content %}
<div class="min-vh-100 d-flex align-items-center justify-content-center"
     style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);">
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-5 col-lg-4">
                <div class="text-center mb-4">
                    <div style="width:64px;height:64px;background:linear-gradient(135deg,#6366f1,#0ea5e9);border-radius:16px;display:inline-flex;align-items:center;justify-content:center;margin-bottom:1rem;">
                        <i class="bi bi-cpu-fill text-white fs-3"></i>
                    </div>
                    <h3 style="color:#fff;font-weight:700;">EngageAI</h3>
                    <p style="color:#94a3b8;font-size:0.875rem;">Student Engagement Detection Platform</p>
                </div>
                <div class="auth-card p-4">
                    <h5 class="fw-bold mb-1">Welcome back</h5>
                    <p class="text-muted mb-4" style="font-size:0.875rem;">Sign in to your account</p>
                    {% if form.errors %}
                    <div class="alert alert-danger py-2" style="font-size:0.85rem;">
                        Invalid username or password.
                    </div>
                    {% endif %}
                    <form method="post">
                        {% csrf_token %}
                        <div class="mb-3">
                            <label class="form-label fw-500" style="font-size:0.875rem;">Username</label>
                            <input type="text" name="username" class="form-control" placeholder="Enter username" required autofocus>
                        </div>
                        <div class="mb-4">
                            <label class="form-label fw-500" style="font-size:0.875rem;">Password</label>
                            <input type="password" name="password" class="form-control" placeholder="Enter password" required>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">
                            <i class="bi bi-box-arrow-in-right me-2"></i>Sign In
                        </button>
                    </form>
                    <p class="text-center mt-3 mb-0" style="font-size:0.875rem;">
                        Don't have an account? <a href="{% url 'accounts:register' %}" class="text-primary fw-bold">Register</a>
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}"""

# ── accounts/register.html ──────────────────────────────
templates['templates/accounts/register.html'] = """{% extends 'base.html' %}
{% block title %}Register - EngageAI{% endblock %}
{% block auth_content %}
<div class="min-vh-100 d-flex align-items-center justify-content-center py-5"
     style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);">
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-6 col-lg-5">
                <div class="text-center mb-4">
                    <div style="width:64px;height:64px;background:linear-gradient(135deg,#6366f1,#0ea5e9);border-radius:16px;display:inline-flex;align-items:center;justify-content:center;margin-bottom:1rem;">
                        <i class="bi bi-cpu-fill text-white fs-3"></i>
                    </div>
                    <h3 style="color:#fff;font-weight:700;">Create Account</h3>
                    <p style="color:#94a3b8;font-size:0.875rem;">Join the EngageAI Platform</p>
                </div>
                <div class="auth-card p-4">
                    {% if form.errors %}
                    <div class="alert alert-danger py-2" style="font-size:0.85rem;">
                        Please fix the errors below.
                        {% for field, errors in form.errors.items %}
                            {% for error in errors %}<br>{{ field }}: {{ error }}{% endfor %}
                        {% endfor %}
                    </div>
                    {% endif %}
                    <form method="post">
                        {% csrf_token %}
                        <div class="row g-3">
                            <div class="col-6">
                                <label class="form-label fw-500" style="font-size:0.875rem;">First Name</label>
                                <input type="text" name="first_name" class="form-control" placeholder="First name">
                            </div>
                            <div class="col-6">
                                <label class="form-label fw-500" style="font-size:0.875rem;">Last Name</label>
                                <input type="text" name="last_name" class="form-control" placeholder="Last name">
                            </div>
                            <div class="col-12">
                                <label class="form-label fw-500" style="font-size:0.875rem;">Username</label>
                                <input type="text" name="username" class="form-control" placeholder="Choose a username" required>
                            </div>
                            <div class="col-12">
                                <label class="form-label fw-500" style="font-size:0.875rem;">Email</label>
                                <input type="email" name="email" class="form-control" placeholder="your@email.com" required>
                            </div>
                            <div class="col-12">
                                <label class="form-label fw-500" style="font-size:0.875rem;">Role</label>
                                <select name="role" class="form-select">
                                    <option value="student">Student</option>
                                    <option value="instructor">Instructor</option>
                                </select>
                            </div>
                            <div class="col-12">
                                <label class="form-label fw-500" style="font-size:0.875rem;">Password</label>
                                <input type="password" name="password1" class="form-control" placeholder="Create a password" required>
                            </div>
                            <div class="col-12">
                                <label class="form-label fw-500" style="font-size:0.875rem;">Confirm Password</label>
                                <input type="password" name="password2" class="form-control" placeholder="Confirm your password" required>
                            </div>
                            <div class="col-12">
                                <button type="submit" class="btn btn-primary w-100">
                                    <i class="bi bi-person-plus me-2"></i>Create Account
                                </button>
                            </div>
                        </div>
                    </form>
                    <p class="text-center mt-3 mb-0" style="font-size:0.875rem;">
                        Already have an account? <a href="{% url 'accounts:login' %}" class="text-primary fw-bold">Sign In</a>
                    </p>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}"""

# ── accounts/profile.html ───────────────────────────────
templates['templates/accounts/profile.html'] = """{% extends 'base.html' %}
{% block title %}Profile - EngageAI{% endblock %}
{% block page_title %}My Profile{% endblock %}
{% block content %}
<div class="row g-4">
    <div class="col-md-4">
        <div class="stat-card text-center">
            <div style="width:80px;height:80px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#0ea5e9);display:inline-flex;align-items:center;justify-content:center;color:#fff;font-size:2rem;font-weight:700;margin-bottom:1rem;">
                {{ user.first_name|first|default:user.username|first|upper }}
            </div>
            <h5 class="fw-bold">{{ user.get_full_name|default:user.username }}</h5>
            <p class="text-muted mb-2" style="font-size:0.875rem;">{{ user.email }}</p>
            <span class="badge py-2 px-3" style="background:#ede9fe;color:#6366f1;border-radius:20px;">{{ user.role|capfirst }}</span>
            <hr>
            <div class="text-start">
                <div class="d-flex justify-content-between mb-2" style="font-size:0.875rem;">
                    <span class="text-muted">Username</span><span class="fw-bold">{{ user.username }}</span>
                </div>
                <div class="d-flex justify-content-between mb-2" style="font-size:0.875rem;">
                    <span class="text-muted">Joined</span><span class="fw-bold">{{ user.date_joined|date:"M d, Y" }}</span>
                </div>
                <div class="d-flex justify-content-between" style="font-size:0.875rem;">
                    <span class="text-muted">Status</span><span class="badge bg-success">Active</span>
                </div>
            </div>
        </div>
    </div>
    <div class="col-md-8">
        <div class="stat-card">
            <h6 class="fw-bold mb-4">Edit Profile</h6>
            <form method="post">
                {% csrf_token %}
                <div class="row g-3">
                    <div class="col-md-6">
                        <label class="form-label" style="font-size:0.875rem;">First Name</label>
                        <input type="text" name="first_name" value="{{ user.first_name }}" class="form-control">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" style="font-size:0.875rem;">Last Name</label>
                        <input type="text" name="last_name" value="{{ user.last_name }}" class="form-control">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" style="font-size:0.875rem;">Email</label>
                        <input type="email" name="email" value="{{ user.email }}" class="form-control">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label" style="font-size:0.875rem;">Phone</label>
                        <input type="text" name="phone" value="{{ user.phone }}" class="form-control" placeholder="+91 ...">
                    </div>
                    <div class="col-12">
                        <label class="form-label" style="font-size:0.875rem;">Bio</label>
                        <textarea name="bio" class="form-control" rows="3" placeholder="Tell us about yourself...">{{ user.bio }}</textarea>
                    </div>
                    <div class="col-12">
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-check-circle me-2"></i>Save Changes
                        </button>
                    </div>
                </div>
            </form>
        </div>
    </div>
</div>
{% endblock %}"""

# ── dashboard/home.html ─────────────────────────────────
templates['templates/dashboard/home.html'] = """{% extends 'base.html' %}
{% block title %}Dashboard - EngageAI{% endblock %}
{% block page_title %}Dashboard{% endblock %}
{% block content %}
<div class="row g-4 mb-4">
    {% if is_instructor %}
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">{{ total_sessions }}</div><div class="stat-label mt-1">Total Sessions</div></div>
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
                <div><div class="stat-value">{{ my_sessions }}</div><div class="stat-label mt-1">My Sessions</div></div>
                <div class="icon" style="background:#ede9fe;color:#6366f1;"><i class="bi bi-camera-video-fill"></i></div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">{{ total_analyses }}</div><div class="stat-label mt-1">Total Analyses</div></div>
                <div class="icon" style="background:#dbeafe;color:#2563eb;"><i class="bi bi-activity"></i></div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">{{ avg_confidence }}%</div><div class="stat-label mt-1">Avg Confidence</div></div>
                <div class="icon" style="background:#dcfce7;color:#16a34a;"><i class="bi bi-graph-up-arrow"></i></div>
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
    {% endif %}
</div>
<div class="row g-4">
    {% if not is_instructor %}
    <div class="col-md-4">
        <div class="stat-card">
            <h6 class="fw-bold mb-3">Engagement Distribution</h6>
            <canvas id="engagementChart" height="220"></canvas>
        </div>
    </div>
    {% endif %}
    <div class="{% if is_instructor %}col-12{% else %}col-md-8{% endif %}">
        <div class="custom-table">
            <div class="p-3 border-bottom d-flex justify-content-between align-items-center">
                <h6 class="fw-bold mb-0">Recent Engagement Records</h6>
                <a href="{% url 'dashboard:reports' %}" class="btn btn-sm btn-outline-primary">View All</a>
            </div>
            <table class="table table-hover mb-0">
                <thead>
                    <tr>
                        <th>Student</th><th>Session</th><th>Level</th><th>Confidence</th><th>Time</th>
                    </tr>
                </thead>
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
                    <tr><td colspan="5" class="text-center text-muted py-4">No records yet. Join a session to start!</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
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
    options: { responsive: true, plugins: { legend: { position: 'bottom' } }, cutout: '65%' }
});
</script>
{% endif %}
{% endblock %}"""

# ── dashboard/reports.html ──────────────────────────────
templates['templates/dashboard/reports.html'] = """{% extends 'base.html' %}
{% block title %}Reports - EngageAI{% endblock %}
{% block page_title %}My Engagement Reports{% endblock %}
{% block content %}
<div class="custom-table">
    <div class="p-3 border-bottom d-flex justify-content-between align-items-center">
        <h6 class="fw-bold mb-0">All Engagement Records</h6>
        <small class="text-muted">{{ records|length }} records</small>
    </div>
    <table class="table table-hover mb-0">
        <thead>
            <tr><th>Session</th><th>Level</th><th>Confidence</th><th>Model</th><th>Date & Time</th></tr>
        </thead>
        <tbody>
            {% for rec in records %}
            <tr>
                <td class="fw-500">{{ rec.session.title|truncatechars:30 }}</td>
                <td><span class="engagement-badge badge-{{ rec.engagement_level }}">{{ rec.get_engagement_level_display }}</span></td>
                <td>{{ rec.confidence_score|floatformat:3 }}</td>
                <td><span class="badge bg-light text-dark border">{{ rec.model_used }}</span></td>
                <td class="text-muted" style="font-size:0.8rem;">{{ rec.timestamp|date:"M d, Y H:i" }}</td>
            </tr>
            {% empty %}
            <tr>
                <td colspan="5" class="text-center text-muted py-5">
                    <i class="bi bi-bar-chart d-block mb-2" style="font-size:2.5rem;"></i>
                    No records yet. Join a session and enable camera monitoring.
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}"""

# ── sessions_app/session_list.html ──────────────────────
templates['templates/sessions_app/session_list.html'] = """{% extends 'base.html' %}
{% block title %}Sessions - EngageAI{% endblock %}
{% block page_title %}Learning Sessions{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <p class="text-muted mb-0" style="font-size:0.875rem;">Manage and join engagement monitoring sessions</p>
    {% if user.role == 'admin' or user.role == 'instructor' %}
    <a href="{% url 'sessions_app:create' %}" class="btn btn-primary">
        <i class="bi bi-plus-lg me-1"></i>New Session
    </a>
    {% endif %}
</div>
<div class="row g-4">
    {% for session in sessions %}
    <div class="col-md-4">
        <div class="stat-card h-100">
            <div class="d-flex justify-content-between align-items-start mb-3">
                <span class="badge {% if session.status == 'active' %}bg-success{% elif session.status == 'scheduled' %}bg-warning text-dark{% else %}bg-secondary{% endif %}">
                    {{ session.get_status_display }}
                </span>
                <small class="text-muted">{{ session.start_time|date:"M d, Y" }}</small>
            </div>
            <h6 class="fw-bold mb-1">{{ session.title }}</h6>
            <p class="text-muted mb-3" style="font-size:0.8rem;">{{ session.description|truncatechars:80 }}</p>
            <div class="d-flex justify-content-between align-items-center">
                <small class="text-muted"><i class="bi bi-person me-1"></i>{{ session.instructor.get_full_name|default:session.instructor.username }}</small>
                <div class="d-flex gap-2">
                    <a href="{% url 'sessions_app:detail' session.pk %}" class="btn btn-sm btn-outline-primary">Details</a>
                    {% if user.role == 'student' %}
                    <a href="{% url 'sessions_app:join' session.pk %}" class="btn btn-sm btn-primary">Join</a>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
    {% empty %}
    <div class="col-12">
        <div class="stat-card text-center py-5">
            <i class="bi bi-camera-video text-muted" style="font-size:3rem;"></i>
            <h6 class="mt-3 text-muted">No sessions yet</h6>
            {% if user.role == 'admin' or user.role == 'instructor' %}
            <a href="{% url 'sessions_app:create' %}" class="btn btn-primary mt-2">Create First Session</a>
            {% endif %}
        </div>
    </div>
    {% endfor %}
</div>
{% endblock %}"""

# ── sessions_app/create_session.html ───────────────────
templates['templates/sessions_app/create_session.html'] = """{% extends 'base.html' %}
{% block title %}Create Session - EngageAI{% endblock %}
{% block page_title %}Create New Session{% endblock %}
{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="stat-card">
            <h6 class="fw-bold mb-4">Session Details</h6>
            <form method="post">
                {% csrf_token %}
                <div class="mb-3">
                    <label class="form-label" style="font-size:0.875rem;">Session Title</label>
                    <input type="text" name="title" class="form-control" placeholder="e.g. Python Programming - Week 3" required>
                </div>
                <div class="mb-3">
                    <label class="form-label" style="font-size:0.875rem;">Description</label>
                    <textarea name="description" class="form-control" rows="3" placeholder="Brief description..."></textarea>
                </div>
                <div class="mb-4">
                    <label class="form-label" style="font-size:0.875rem;">Start Time</label>
                    <input type="datetime-local" name="start_time" class="form-control" required>
                </div>
                <button type="submit" class="btn btn-primary w-100">
                    <i class="bi bi-plus-circle me-2"></i>Create Session
                </button>
            </form>
        </div>
    </div>
</div>
{% endblock %}"""

# ── sessions_app/session_detail.html ───────────────────
templates['templates/sessions_app/session_detail.html'] = """{% extends 'base.html' %}
{% block title %}Session Detail - EngageAI{% endblock %}
{% block page_title %}Session: {{ session.title }}{% endblock %}
{% block content %}
<div class="row g-4">
    <div class="col-md-8">
        <div class="custom-table">
            <div class="p-3 border-bottom d-flex justify-content-between align-items-center">
                <h6 class="fw-bold mb-0">Engagement Records</h6>
                <span class="badge" style="background:#ede9fe;color:#6366f1;">{{ records|length }} records</span>
            </div>
            <table class="table table-hover mb-0">
                <thead><tr><th>Student</th><th>Level</th><th>Confidence</th><th>Model</th><th>Time</th></tr></thead>
                <tbody>
                    {% for rec in records %}
                    <tr>
                        <td>{{ rec.student.get_full_name|default:rec.student.username }}</td>
                        <td><span class="engagement-badge badge-{{ rec.engagement_level }}">{{ rec.get_engagement_level_display }}</span></td>
                        <td>{{ rec.confidence_score|floatformat:3 }}</td>
                        <td><span class="badge bg-light text-dark border" style="font-size:0.7rem;">{{ rec.model_used }}</span></td>
                        <td class="text-muted" style="font-size:0.8rem;">{{ rec.timestamp|date:"H:i:s" }}</td>
                    </tr>
                    {% empty %}
                    <tr><td colspan="5" class="text-center text-muted py-4">No engagement records yet</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    <div class="col-md-4">
        <div class="stat-card mb-4">
            <h6 class="fw-bold mb-3">Session Info</h6>
            <div class="mb-2 d-flex justify-content-between" style="font-size:0.875rem;">
                <span class="text-muted">Status</span>
                <span class="badge {% if session.status == 'active' %}bg-success{% elif session.status == 'scheduled' %}bg-warning text-dark{% else %}bg-secondary{% endif %}">{{ session.get_status_display }}</span>
            </div>
            <div class="mb-2 d-flex justify-content-between" style="font-size:0.875rem;">
                <span class="text-muted">Instructor</span>
                <span class="fw-bold">{{ session.instructor.get_full_name|default:session.instructor.username }}</span>
            </div>
            <div class="mb-2 d-flex justify-content-between" style="font-size:0.875rem;">
                <span class="text-muted">Start Time</span>
                <span class="fw-bold">{{ session.start_time|date:"M d, Y H:i" }}</span>
            </div>
            <div class="d-flex justify-content-between" style="font-size:0.875rem;">
                <span class="text-muted">Students</span>
                <span class="fw-bold">{{ enrollments|length }} enrolled</span>
            </div>
            {% if user.role == 'student' %}
            <a href="{% url 'sessions_app:join' session.pk %}" class="btn btn-primary w-100 mt-3">
                <i class="bi bi-camera-video me-2"></i>Join & Monitor
            </a>
            {% endif %}
        </div>
        <div class="stat-card">
            <h6 class="fw-bold mb-3">Enrolled Students</h6>
            {% for enroll in enrollments %}
            <div class="d-flex align-items-center gap-2 mb-2">
                <div style="width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#0ea5e9);display:inline-flex;align-items:center;justify-content:center;color:#fff;font-size:0.75rem;font-weight:700;flex-shrink:0;">
                    {{ enroll.student.first_name|first|default:enroll.student.username|first|upper }}
                </div>
                <div>
                    <div style="font-size:0.875rem;font-weight:500;">{{ enroll.student.get_full_name|default:enroll.student.username }}</div>
                    <small class="text-muted">Joined {{ enroll.enrolled_at|timesince }} ago</small>
                </div>
            </div>
            {% empty %}
            <p class="text-muted text-center py-2" style="font-size:0.875rem;">No students enrolled</p>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}"""

# ── sessions_app/live_monitor.html ─────────────────────
templates['templates/sessions_app/live_monitor.html'] = """{% extends 'base.html' %}
{% block title %}Live Monitor - EngageAI{% endblock %}
{% block page_title %}Live Session: {{ session.title }}{% endblock %}
{% block content %}
<div class="row g-4">
    <div class="col-md-7">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="fw-bold mb-0"><i class="bi bi-camera-video text-primary me-2"></i>Camera Feed</h6>
                <span id="status-badge" class="badge bg-secondary">Stopped</span>
            </div>
            <div style="background:#0f172a;border-radius:12px;overflow:hidden;position:relative;min-height:300px;">
                <video id="webcam" autoplay muted playsinline style="width:100%;max-height:380px;object-fit:cover;"></video>
            </div>
            <div class="d-flex gap-2 mt-3">
                <button id="startBtn" class="btn btn-primary" onclick="startMonitoring()">
                    <i class="bi bi-play-fill me-1"></i>Start Monitoring
                </button>
                <button id="stopBtn" class="btn btn-outline-danger d-none" onclick="stopMonitoring()">
                    <i class="bi bi-stop-fill me-1"></i>Stop
                </button>
            </div>
        </div>
    </div>
    <div class="col-md-5">
        <div class="stat-card mb-4">
            <h6 class="fw-bold mb-3">Current Engagement</h6>
            <div class="text-center py-2">
                <div id="engagement-level" style="font-size:2rem;font-weight:700;color:#6366f1;">--</div>
                <div id="engagement-conf" class="text-muted mt-1" style="font-size:0.875rem;">Confidence: --</div>
                <canvas id="probChart" height="160" class="mt-3"></canvas>
            </div>
        </div>
        <div class="stat-card">
            <h6 class="fw-bold mb-3">Session Info</h6>
            <div class="d-flex justify-content-between mb-2" style="font-size:0.875rem;">
                <span class="text-muted">Session</span>
                <span class="fw-bold">{{ session.title|truncatechars:20 }}</span>
            </div>
            <div class="d-flex justify-content-between mb-2" style="font-size:0.875rem;">
                <span class="text-muted">Analyses Done</span>
                <span class="fw-bold" id="analysis-count">0</span>
            </div>
            <div class="d-flex justify-content-between" style="font-size:0.875rem;">
                <span class="text-muted">Model</span>
                <span class="fw-bold">Hybrid Ensemble</span>
            </div>
        </div>
    </div>
</div>
{% endblock %}
{% block extra_js %}
<script>
let stream = null, intervalId = null, analysisCount = 0, probChart = null;
const SESSION_ID = {{ session.id }};

function initChart() {
    const ctx = document.getElementById('probChart').getContext('2d');
    probChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Very Low', 'Low', 'High', 'Very High'],
            datasets: [{
                data: [0.25, 0.25, 0.25, 0.25],
                backgroundColor: ['#fee2e2','#fef9c3','#dbeafe','#dcfce7'],
                borderColor: ['#ef4444','#f59e0b','#3b82f6','#10b981'],
                borderWidth: 2, borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            scales: { y: { max: 1, beginAtZero: true } },
            plugins: { legend: { display: false } }
        }
    });
}

async function startMonitoring() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
        document.getElementById('webcam').srcObject = stream;
        document.getElementById('startBtn').classList.add('d-none');
        document.getElementById('stopBtn').classList.remove('d-none');
        document.getElementById('status-badge').className = 'badge bg-success';
        document.getElementById('status-badge').textContent = 'Live';
        initChart();
        intervalId = setInterval(captureAndAnalyze, 3000);
    } catch(e) { alert('Camera access denied: ' + e.message); }
}

function stopMonitoring() {
    if (stream) stream.getTracks().forEach(t => t.stop());
    clearInterval(intervalId);
    document.getElementById('startBtn').classList.remove('d-none');
    document.getElementById('stopBtn').classList.add('d-none');
    document.getElementById('status-badge').className = 'badge bg-secondary';
    document.getElementById('status-badge').textContent = 'Stopped';
}

function captureAndAnalyze() {
    const video = document.getElementById('webcam');
    const canvas = document.createElement('canvas');
    canvas.width = 320; canvas.height = 240;
    canvas.getContext('2d').drawImage(video, 0, 0, 320, 240);
    const frameData = canvas.toDataURL('image/jpeg', 0.7);
    fetch('/sessions/analyze-frame/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
        body: JSON.stringify({ session_id: SESSION_ID, frame: frameData })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            const r = data.result;
            const map = { very_low:'Very Low', low:'Low', high:'High', very_high:'Very High' };
            document.getElementById('engagement-level').textContent = map[r.level] || r.level;
            document.getElementById('engagement-conf').textContent = 'Confidence: ' + (r.confidence * 100).toFixed(1) + '%';
            analysisCount++;
            document.getElementById('analysis-count').textContent = analysisCount;
            if (probChart && r.probabilities) {
                const p = r.probabilities;
                probChart.data.datasets[0].data = [p.very_low, p.low, p.high, p.very_high];
                probChart.update();
            }
        }
    }).catch(console.error);
}

function getCookie(name) {
    let v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
    return v ? v[2] : null;
}
</script>
{% endblock %}"""

# ── admin_panel/dashboard.html ──────────────────────────
templates['templates/admin_panel/dashboard.html'] = """{% extends 'base.html' %}
{% block title %}Admin Dashboard - EngageAI{% endblock %}
{% block page_title %}Control Panel{% endblock %}
{% block content %}
<div class="row g-4 mb-4">
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">{{ total_users }}</div><div class="stat-label mt-1">Total Students</div></div>
                <div class="icon" style="background:#ede9fe;color:#6366f1;"><i class="bi bi-people-fill"></i></div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">{{ total_sessions }}</div><div class="stat-label mt-1">Total Sessions</div></div>
                <div class="icon" style="background:#dbeafe;color:#2563eb;"><i class="bi bi-camera-video-fill"></i></div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">{{ total_analyses }}</div><div class="stat-label mt-1">Total Analyses</div></div>
                <div class="icon" style="background:#dcfce7;color:#16a34a;"><i class="bi bi-activity"></i></div>
            </div>
        </div>
    </div>
    <div class="col-md-3">
        <div class="stat-card">
            <div class="d-flex justify-content-between align-items-start">
                <div><div class="stat-value">94.25%</div><div class="stat-label mt-1">Hybrid Accuracy</div></div>
                <div class="icon" style="background:#fef9c3;color:#d97706;"><i class="bi bi-cpu-fill"></i></div>
            </div>
        </div>
    </div>
</div>
<div class="row g-4 mb-4">
    <div class="col-md-5">
        <div class="stat-card">
            <h6 class="fw-bold mb-3">Engagement Distribution</h6>
            <canvas id="distChart" height="250"></canvas>
        </div>
    </div>
    <div class="col-md-7">
        <div class="stat-card">
            <h6 class="fw-bold mb-3">Model Performance Comparison</h6>
            <canvas id="modelChart" height="250"></canvas>
        </div>
    </div>
</div>
<div class="custom-table">
    <div class="p-3 border-bottom"><h6 class="fw-bold mb-0">Recent Sessions</h6></div>
    <table class="table table-hover mb-0">
        <thead><tr><th>Session</th><th>Instructor</th><th>Status</th><th>Date</th></tr></thead>
        <tbody>
            {% for s in recent_sessions %}
            <tr>
                <td class="fw-500">{{ s.title }}</td>
                <td>{{ s.instructor.get_full_name|default:s.instructor.username }}</td>
                <td><span class="badge {% if s.status == 'active' %}bg-success{% elif s.status == 'scheduled' %}bg-warning text-dark{% else %}bg-secondary{% endif %}">{{ s.get_status_display }}</span></td>
                <td class="text-muted">{{ s.created_at|date:"M d, Y" }}</td>
            </tr>
            {% empty %}
            <tr><td colspan="4" class="text-center text-muted py-4">No sessions yet</td></tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
{% block extra_js %}
<script>
const distData = {{ dist_data|safe }};
new Chart(document.getElementById('distChart').getContext('2d'), {
    type: 'pie',
    data: {
        labels: ['Very Low', 'Low', 'High', 'Very High'],
        datasets: [{ data: [distData.very_low||0, distData.low||0, distData.high||0, distData.very_high||0], backgroundColor: ['#fee2e2','#fef9c3','#dbeafe','#dcfce7'], borderColor: ['#ef4444','#f59e0b','#3b82f6','#10b981'], borderWidth: 2 }]
    },
    options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
});
new Chart(document.getElementById('modelChart').getContext('2d'), {
    type: 'bar',
    data: {
        labels: ['1D CNN', '1D ResNet', 'CNN Bagging', 'ResNet Bagging', 'Hybrid'],
        datasets: [{ label: 'Accuracy (%)', data: [90, 90.25, 93.25, 93.75, 94.25], backgroundColor: ['#e0e7ff','#dbeafe','#c7d2fe','#bfdbfe','#6366f1'], borderColor: '#6366f1', borderWidth: 2, borderRadius: 8 }]
    },
    options: { responsive: true, scales: { y: { min: 85, max: 96 } }, plugins: { legend: { display: false } } }
});
</script>
{% endblock %}"""

# ── admin_panel/users.html ──────────────────────────────
templates['templates/admin_panel/users.html'] = """{% extends 'base.html' %}
{% block title %}Users - EngageAI{% endblock %}
{% block page_title %}User Management{% endblock %}
{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <p class="text-muted mb-0" style="font-size:0.875rem;">{{ users|length }} total users registered</p>
    <input type="text" id="searchInput" class="form-control" placeholder="Search users..." style="width:220px;" onkeyup="filterTable()">
</div>
<div class="custom-table">
    <table class="table table-hover mb-0" id="usersTable">
        <thead><tr><th>#</th><th>Name</th><th>Username</th><th>Email</th><th>Role</th><th>Joined</th><th>Status</th></tr></thead>
        <tbody>
            {% for u in users %}
            <tr>
                <td class="text-muted">{{ forloop.counter }}</td>
                <td>
                    <div class="d-flex align-items-center gap-2">
                        <div style="width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#6366f1,#0ea5e9);display:inline-flex;align-items:center;justify-content:center;color:#fff;font-weight:600;font-size:0.8rem;flex-shrink:0;">
                            {{ u.first_name|first|default:u.username|first|upper }}
                        </div>
                        <span class="fw-500" style="font-size:0.875rem;">{{ u.get_full_name|default:u.username }}</span>
                    </div>
                </td>
                <td style="font-size:0.875rem;">@{{ u.username }}</td>
                <td style="font-size:0.875rem;">{{ u.email }}</td>
                <td>
                    <span class="badge py-1 px-2" style="border-radius:20px;font-size:0.75rem;{% if u.role == 'admin' %}background:#fee2e2;color:#b91c1c;{% elif u.role == 'instructor' %}background:#ede9fe;color:#6366f1;{% else %}background:#dbeafe;color:#1d4ed8;{% endif %}">
                        {{ u.role|capfirst }}
                    </span>
                </td>
                <td class="text-muted" style="font-size:0.8rem;">{{ u.date_joined|date:"M d, Y" }}</td>
                <td>{% if u.is_active %}<span class="badge bg-success">Active</span>{% else %}<span class="badge bg-secondary">Inactive</span>{% endif %}</td>
            </tr>
            {% empty %}
            <tr><td colspan="7" class="text-center text-muted py-5">No users found</td></tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}
{% block extra_js %}
<script>
function filterTable() {
    const input = document.getElementById('searchInput').value.toLowerCase();
    document.querySelectorAll('#usersTable tbody tr').forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(input) ? '' : 'none';
    });
}
</script>
{% endblock %}"""

# ── admin_panel/analytics.html ──────────────────────────
templates['templates/admin_panel/analytics.html'] = """{% extends 'base.html' %}
{% block title %}Analytics - EngageAI{% endblock %}
{% block page_title %}Session Analytics{% endblock %}
{% block content %}
<div class="custom-table">
    <div class="p-3 border-bottom"><h6 class="fw-bold mb-0">Session Performance Overview</h6></div>
    <table class="table table-hover mb-0">
        <thead><tr><th>Session Title</th><th>Instructor</th><th>Students</th><th>Analyses</th><th>Avg Confidence</th><th>Status</th><th>Date</th></tr></thead>
        <tbody>
            {% for s in sessions %}
            <tr>
                <td class="fw-500">{{ s.title|truncatechars:30 }}</td>
                <td style="font-size:0.875rem;">{{ s.instructor.get_full_name|default:s.instructor.username }}</td>
                <td><span class="badge" style="background:#dbeafe;color:#1d4ed8;">{{ s.student_count }}</span></td>
                <td><span class="badge" style="background:#dcfce7;color:#15803d;">{{ s.record_count }}</span></td>
                <td>
                    {% if s.avg_confidence %}
                    <span style="font-size:0.875rem;">{{ s.avg_confidence|floatformat:3 }}</span>
                    {% else %}<span class="text-muted">—</span>{% endif %}
                </td>
                <td><span class="badge {% if s.status == 'active' %}bg-success{% elif s.status == 'scheduled' %}bg-warning text-dark{% else %}bg-secondary{% endif %}">{{ s.get_status_display }}</span></td>
                <td class="text-muted" style="font-size:0.8rem;">{{ s.created_at|date:"M d, Y" }}</td>
            </tr>
            {% empty %}
            <tr><td colspan="7" class="text-center text-muted py-5">
                <i class="bi bi-graph-up d-block mb-2" style="font-size:2.5rem;"></i>
                No sessions found.
            </td></tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endblock %}"""

# ── admin_panel/model_config.html ───────────────────────
templates['templates/admin_panel/model_config.html'] = """{% extends 'base.html' %}
{% block title %}Model Config - EngageAI{% endblock %}
{% block page_title %}Model Configuration{% endblock %}
{% block content %}
<div class="row g-4">
    <div class="col-md-8">
        <div class="stat-card">
            <h6 class="fw-bold mb-4">Trained Models</h6>
            {% if model_files %}
            <div class="list-group list-group-flush">
                {% for f in model_files %}
                <div class="list-group-item d-flex align-items-center gap-3 px-0">
                    <div style="width:40px;height:40px;border-radius:10px;background:#ede9fe;color:#6366f1;display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0;">
                        <i class="bi bi-cpu"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="fw-bold" style="font-size:0.875rem;">{{ f }}</div>
                        <small class="text-muted">Keras Model File</small>
                    </div>
                    <span class="badge bg-success">Ready</span>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="text-center py-5">
                <i class="bi bi-cpu text-muted" style="font-size:3rem;"></i>
                <h6 class="mt-3 text-muted">No models trained yet</h6>
                <p class="text-muted" style="font-size:0.875rem;">Run the commands below to train models</p>
                <div class="bg-light p-3 rounded mt-3 text-start" style="font-size:0.8rem;font-family:monospace;">
                    python ml_engine/generate_dataset.py<br>
                    python ml_engine/train_models.py
                </div>
            </div>
            {% endif %}
        </div>
    </div>
    <div class="col-md-4">
        <div class="stat-card mb-4">
            <h6 class="fw-bold mb-3">Model Accuracies</h6>
            {% for label, val, color in accuracy_bars %}
            <div class="mb-3">
                <div class="d-flex justify-content-between mb-1" style="font-size:0.8rem;">
                    <span>{{ label }}</span><span class="fw-bold">{{ val }}%</span>
                </div>
                <div class="progress" style="height:6px;border-radius:3px;">
                    <div class="progress-bar" style="width:{{ val }}%;background:{{ color }};"></div>
                </div>
            </div>
            {% endfor %}
        </div>
        <div class="stat-card">
            <h6 class="fw-bold mb-3">Quick Actions</h6>
            <div class="d-grid gap-2">
                <button class="btn btn-outline-primary btn-sm" onclick="alert('Run: python ml_engine/train_models.py')">
                    <i class="bi bi-arrow-repeat me-2"></i>Retrain Models
                </button>
                <button class="btn btn-outline-secondary btn-sm" onclick="alert('Run: python ml_engine/generate_dataset.py')">
                    <i class="bi bi-database me-2"></i>Regenerate Dataset
                </button>
            </div>
        </div>
    </div>
</div>
{% endblock %}"""

# Write all template files
for filepath, content in templates.items():
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'✓ Written: {filepath}')

print('\nALL TEMPLATES WRITTEN SUCCESSFULLY!')
