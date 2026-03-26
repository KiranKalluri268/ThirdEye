# 🧑‍💻 Senior Developer Code Review — `engagement_project`

> **Overall Rating: 6.5 / 10**
> A well-scoped, functional student engagement detection system with a thoughtful ML pipeline. Solid fundamentals let down by critical security gaps, a polluted root directory, and absent tests.

---

## 📊 Rating Summary

| Aspect | Score | Verdict |
|---|---|---|
| **Architecture & Structure** | 7/10 | ✅ Clean Django app separation |
| **Code Quality** | 7/10 | ✅ Readable, mostly consistent |
| **Security** | 3/10 | 🚨 Critical issues |
| **ML Engineering** | 7.5/10 | ✅ Genuinely impressive |
| **Database Design** | 7/10 | ✅ Well normalised |
| **Modern Practices** | 5/10 | ⚠️ Mixed |
| **Testing** | 1/10 | ❌ Effectively zero |
| **Developer Experience** | 4/10 | ⚠️ Root dir was messy (now cleaned) |

---

## ✅ What's Done Well

### Architecture
- **Proper Django app separation**: `accounts`, `dashboard`, `sessions_app`, `admin_panel`, `ml_engine` — each has a clear, single responsibility.
- **Custom User Model**: Using `AbstractUser` with `AUTH_USER_MODEL` from the start avoids painful migrations later.
- **`select_related` on queries**: Used correctly in views, preventing N+1 database query problems.
- **`get_object_or_404`**: Used consistently — no raw `.get()` calls that crash with unhandled exceptions.

### ML Engine (`ml_engine/inference.py`)
- **Graceful fallback chain**: MediaPipe → OpenCV Haar Cascade. Production-quality resilience.
- **EAR (Eye Aspect Ratio) gating**: Hard gates override the composite score based on eye state — physiologically grounded.
- **Temporal smoothing**: `_score_history` averaging prevents flickering labels between frames.
- **Lazy model loading**: `load_ml` only runs once, guarded by `_ml_loaded`, avoiding TensorFlow model reloads on every request.
- **Ensemble training**: `train_models.py` implements bagging with bootstrap sampling over 1D CNN and 1D ResNet — beyond what most university projects attempt.

---

## 🚨 Critical Issues

### 1. Hardcoded secrets in `settings.py`
```python
SECRET_KEY = 'django-insecure-your-secret-key-change-this-in-production'
DEBUG = True
ALLOWED_HOSTS = ['*']
'PASSWORD': 'root',
```
Move everything to `.env` using `python-decouple` (already in `requirements.txt`):
```python
from decouple import config
SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])
```

### 2. Broken `admin_required` decorator
```python
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):  # missing @wraps(view_func)
        if not request.user.is_authenticated or request.user.role ...
```
- Missing `@functools.wraps(view_func)` — breaks Django's URL naming.
- `@login_required` is not applied first — an unauthenticated request will `AttributeError` crash on `.role`.

### 3. `profile_view` bypasses form validation
```python
user.first_name = request.POST.get('first_name', '')
user.save()  # no validation — user can POST any field
```
Use a `ModelForm` to handle validation and field whitelisting.

### 4. Hardcoded model accuracy in `model_config` view
`accuracy_bars` in `admin_panel/views.py` shows static numbers. Should read from `ml_engine/saved_models/accuracy_results.json` (which `train_models.py` already writes).

### 5. `__str__` typo in `CustomUser`
```python
return f"{self.username} ({self.role}^)"  # stray '^' character
```

---

## ❌ Testing — 1/10

All `tests.py` files are blank. Minimum required:
- Role access: can a student access instructor-only views?
- `analyze_frame`: does it return the correct JSON shape?
- ML: does `predict_engagement` return a valid dict with expected keys?

---

## 🛠️ Prioritised Action Plan

| Priority | Action |
|---|---|
| 🔴 **P0** | Move secrets to `.env` via `python-decouple` |
| 🔴 **P0** | Fix `admin_required` — add `@wraps` and chain with `@login_required` |
| 🟠 **P1** | Replace manual POST parsing in `profile_view` with a `ModelForm` |
| 🟠 **P1** | Read `accuracy_results.json` dynamically in `model_config` view |
| 🟡 **P2** | Add `LOGGING`, `LANGUAGE_CODE`, `TIME_ZONE` to `settings.py` |
| 🟡 **P2** | Add global mutable state thread-safety note to `inference.py` |
| 🟢 **P3** | Write tests for auth, inference endpoint, and role access |
| 🟢 **P3** | Fix the `^` typo in `CustomUser.__str__` |
