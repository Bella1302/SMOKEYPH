"""
Django settings for Smokey Peeks project.
"""

import os
from pathlib import Path
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env(path: Path) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(path)
    except ImportError:
        if not path.is_file():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if not key or key in os.environ:
                continue
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            os.environ[key] = value


_load_env(BASE_DIR / ".env")

SECRET_KEY = os.environ.get('SECRET_KEY', os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-change-me-in-production'))

DEBUG = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "smokey-peeks.onrender.com",
    "smokeypeeks-ph.com",
    "www.smokeypeeks-ph.com",
]
if os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
    ALLOWED_HOSTS.append(os.environ.get('RENDER_EXTERNAL_HOSTNAME'))

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'main',
]

if os.environ.get('CLOUDINARY_URL'):
    INSTALLED_APPS = ['cloudinary_storage', 'cloudinary'] + INSTALLED_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'main.middleware.VisitCounterMiddleware',
]

ROOT_URLCONF = 'smokey_peeks.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'smokey_peeks.wsgi.application'

# DATABASE_URL = os.environ.get("DATABASE_URL")

# if DATABASE_URL:
#     DATABASES = {
#         "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)
#     }
# else:
#     # fallback for local dev
#     DATABASES = {
#         "default": {
#             "ENGINE": "django.db.backends.sqlite3",
#             "NAME": BASE_DIR / "db.sqlite3",
#         }
#     }

if os.environ.get('DATABASE_URL'):
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    DATABASES = {
        'default': dj_database_url.config(
            default=db_url,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # fallback for local dev
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

if os.environ.get('CLOUDINARY_URL'):
    STORAGES = {
        'default': {
            'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
        },
        'staticfiles': {
            'BACKEND': (
                'whitenoise.storage.CompressedStaticFilesStorage'
                if not DEBUG
                else 'django.contrib.staticfiles.storage.StaticFilesStorage'
            ),
        },
    }
elif not DEBUG:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
        },
    }
else:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email (console backend for development; configure SMTP for production)
EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Smokey Peeks <smokeypeekscebu@gmail.com>')
