```markdown

\# ThirdEye — Student Engagement Detection System

A real-time AI-powered student engagement detection web application built with Django,

MediaPipe, TensorFlow, and OpenCV. The system monitors student engagement levels during

live learning sessions using webcam feeds.



\---



\## 🚀 Features



\- 📷 Real-time face detection \& engagement scoring via webcam

\- 😊 4-level engagement classification: Very Low / Low / High / Very High

\- 👁️ Eye openness (EAR), gaze direction \& head pose analysis

\- 🧠 MediaPipe FaceMesh with anatomical face validation (rejects hands/objects)

\- 📊 Live confidence scores, detection details \& engagement charts

\- 📋 Session-wise engagement reports for instructors \& students

\- 👥 Multi-role system: Admin / Instructor / Student

\- 🔒 Django authentication with role-based access control



\---



\## 🛠️ Tech Stack



| Layer | Technology |

|---|---|

| Backend | Django 4.2.7, Django REST Framework |

| AI/ML | TensorFlow 2.15, MediaPipe 0.10.9, OpenCV |

| Database | MySQL |

| Frontend | HTML5, Bootstrap 5, JavaScript, Chart.js |

| WebSocket | Django Channels 4.0 |



\---



\## 📁 Project Structure



```

engagement\_project/

├── engagement\_project/     # Django settings \& URLs

├── sessions\_app/           # Sessions, enrollment, live monitoring

├── dashboard/              # Reports, analytics, home

├── accounts/               # User auth \& role management

├── ml\_engine/              # inference.py — AI engagement engine

│   └── saved\_models/       # Trained .keras model files

├── templates/              # HTML templates

├── static/                 # CSS, JS, images

├── requirements.txt

└── manage.py

```



\---



\## ⚙️ Installation



\### Prerequisites

\- Python 3.11

\- MySQL Server

\- Git



\### Step 1 — Clone the repository

```bash

git clone https://github.com/yourusername/engagement\_project.git

cd engagement\_project

```



\### Step 2 — Create virtual environment

```bash

python -m venv venv



\# Windows

venv\\Scripts\\activate



\# Linux/Mac

source venv/bin/activate

```



\### Step 3 — Install dependencies

```bash

pip install --upgrade pip

pip install -r requirements.txt

```



\### Step 4 — Fix version conflicts (IMPORTANT)

```bash

pip uninstall jax jaxlib -y

pip install "numpy==1.26.4" "ml-dtypes==0.2.0" --force-reinstall

```



\### Step 5 — Configure environment

Create a `.env` file in the root directory:

```env

SECRET\_KEY=your-secret-key-here

DEBUG=True

DB\_NAME=engagement\_db

DB\_USER=root

DB\_PASSWORD=yourpassword

DB\_HOST=localhost

DB\_PORT=3306

```



\### Step 6 — Setup database

```bash

\# Create MySQL database first

mysql -u root -p -e "CREATE DATABASE engagement\_db;"



\# Run migrations

python manage.py makemigrations

python manage.py migrate

```



\### Step 7 — Create superuser

```bash

python manage.py createsuperuser

```



\### Step 8 — Run the server

```bash

python manage.py runserver

```



Visit: \*\*http://127.0.0.1:8000\*\*



\---



\## 👤 Default Roles



| Role | Access |

|---|---|

| \*\*Admin\*\* | Full access, user management, analytics |

| \*\*Instructor\*\* | Create sessions, view all student reports |

| \*\*Student\*\* | Join sessions, view personal reports |



\---



\## 🧠 How Engagement Detection Works



1\. Student webcam frame is captured every 2 seconds

2\. \*\*MediaPipe FaceMesh\*\* maps 468 facial landmarks

3\. \*\*Anatomical validation\*\* checks face geometry (rejects hands/objects)

4\. \*\*EAR (Eye Aspect Ratio)\*\* determines eye openness — hard gate

5\. \*\*Gaze score\*\* measures iris offset from eye center

6\. \*\*Head yaw\*\* detects looking away

7\. Final weighted score maps to engagement level:

&#x20;  - `score > 0.65` → Very High

&#x20;  - `score 0.45–0.65` → High

&#x20;  - `score 0.25–0.45` → Low

&#x20;  - `score < 0.25` → Very Low



\---



\## 🐛 Known Issues \& Fixes



| Issue | Fix |

|---|---|

| `mp.solutions` AttributeError | Use `mediapipe==0.10.9` |

| numpy 2.x breaks TensorFlow | Pin `numpy==1.26.4` |

| jax pulls wrong ml-dtypes | `pip uninstall jax jaxlib -y` |

| Hand detected as face | FaceMesh-only mode with anatomical validation |

| Closed eyes showing High | EAR hard gate — eyes are 40% weight |



\---



\## 📊 Reports



\- \*\*Students\*\* see their own per-session engagement history

\- \*\*Instructors\*\* see all students' records across their sessions

\- Records include: engagement level, confidence %, model used, timestamp



\---



\## 📦 Requirements



See `requirements.txt` for the full list.

Key packages:

```

Django==4.2.7

tensorflow-intel==2.15.0

mediapipe==0.10.9

numpy==1.26.4

opencv-contrib-python==4.11.0.86

ml-dtypes==0.2.0

```



\---





\## Run it



```cmd

python manage.py runserver

```



