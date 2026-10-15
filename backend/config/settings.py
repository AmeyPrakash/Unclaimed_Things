"""
Django settings for The Unclaimed Things Network (UTN).
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from project root (.env) or local .env
env_path = BASE_DIR.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv(BASE_DIR / '.env')

# Core Security & Debug
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'utn-dev-secret-key-change-in-prod')
DEBUG = os.environ.get('DJANGO_DEBUG', 'true').strip().lower() in ('true', '1', 'yes')

allowed_hosts_raw = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [h.strip() for h in allowed_hosts_raw.split(',') if h.strip()]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'corsheaders',
    # Modular monolith apps
    'common.apps.CommonConfig',
    'accounts.apps.AccountsConfig',
    'locations.apps.LocationsConfig',
    'reports.apps.ReportsConfig',
    'matching.apps.MatchingConfig',
    'claims.apps.ClaimsConfig',
    'custody.apps.CustodyConfig',
    'audit.apps.AuditConfig',
]

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'common.middleware.RequestIdMiddleware',
    'common.middleware.SecurityHeadersMiddleware',
    'django.middleware.common.CommonMiddleware',

    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database configuration (Neon Postgres + pgvector)
# Tests and migrations require direct (unpooled) connections to avoid PgBouncer transaction/session limits
is_testing_or_migration = any(cmd in sys.argv for cmd in ('test', 'migrate', 'makemigrations'))
if is_testing_or_migration and os.environ.get('DATABASE_URL_UNPOOLED'):
    database_url = os.environ.get('DATABASE_URL_UNPOOLED')
else:
    database_url = os.environ.get('DATABASE_URL')
conn_age = 600

if database_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=database_url,
            conn_max_age=conn_age,
            ssl_require=True
        )
    }
    DATABASES['default'].setdefault('OPTIONS', {})
    DATABASES['default']['OPTIONS'].update({
        'keepalives': 1,
        'keepalives_idle': 30,
        'keepalives_interval': 10,
        'keepalives_count': 5,
    })
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

if 'test' in sys.argv:
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]


# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files & Media files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
UPLOAD_MAX_BYTES = int(os.environ.get('UPLOAD_MAX_BYTES', 5242880))  # 5MB default

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Cache Configuration (LocMemCache for dev & throttling)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'utn-throttle-cache',
    }
}

# Django REST Framework Settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'auth_login': '10/minute',
        'auth_register': '5/minute',
        'claim_create': '20/minute',
        'report_create': '30/minute',
        'search': '120/minute',
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'common.exceptions.custom_exception_handler',
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
]

# NVIDIA NIM AI Configuration
NIM_ENABLED = os.environ.get('NIM_ENABLED', 'false').strip().lower() in ('true', '1', 'yes')
NIM_BASE_URL = os.environ.get('NIM_BASE_URL', 'https://integrate.api.nvidia.com/v1').rstrip('/')
NIM_API_KEY = os.environ.get('NIM_API_KEY', '')
NIM_EMBEDDING_MODEL = os.environ.get('NIM_EMBEDDING_MODEL', 'nvidia/nemotron-3-embed-1b')
NIM_TIMEOUT_SECONDS = int(os.environ.get('NIM_TIMEOUT_SECONDS', 20))
NIM_EMBEDDING_DIMENSION = 2048  # Verified dimension from live NVIDIA NIM model

# Security Hardening & Headers (TRD Section 9)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

