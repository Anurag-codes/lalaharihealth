"""
Django settings for config project.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.1/ref/settings/
"""

from datetime import timedelta
from pathlib import Path

from decouple import Csv, config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())


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
    'rest_framework_simplejwt',
    'corsheaders',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    # LalahariHealth apps
    'apps.core',
    'apps.accounts',
    'apps.doctors',
    'apps.patients',
    'apps.treatments',
    'apps.hospitals',
    'apps.consultations',
    'apps.appointments',
    'apps.payments',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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


# Database
# SQLite remains the local default; production selects PostgreSQL through .env.
DATABASE_ENGINE = config('DB_ENGINE', default='django.db.backends.sqlite3')

if DATABASE_ENGINE == 'django.db.backends.sqlite3':
    DATABASES = {
        'default': {
            'ENGINE': DATABASE_ENGINE,
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': DATABASE_ENGINE,
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='127.0.0.1'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': config('DB_CONN_MAX_AGE', default=60, cast=int),
        }
    }


# Custom user model
AUTH_USER_MODEL = 'accounts.User'


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_TZ = True


# Static & media files

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'LalahariHealth API',
    'DESCRIPTION': (
        'Mobile booking flow:\n\n'
        '1. Obtain a JWT from POST /api/v1/auth/token/ using an existing account. '
        'Use `Authorization: Bearer ACCESS_TOKEN` for all mobile endpoints. Account signup/OTP is not implemented here.\n'
        '2. POST /api/v1/consultations/ with patient_name, patient_age, patient_gender, patient_phone and mode. '
        'Store the returned consultation id. Accounts may book for a family member.\n'
        '3. GET /api/v1/consultations/conditions/ for dropdown options; '
        'PUT /api/v1/consultations/{id}/history/ with condition (optional/null), symptoms (optional), '
        'duration_value, duration_unit, ongoing_medication and treatment_details (optional).\n'
        '4. Optional POST /api/v1/consultations/{id}/documents/ as multipart with one file per request. '
        'PDF/PNG/JPG up to 10 MB. Skip means no upload call; private downloads require authentication.\n'
        '5. GET /api/v1/appointments/slots/?date=YYYY-MM-DD. Dates are Asia/Kolkata; '
        'slots are admin-configured, future only, between 08:00 and 23:59. Empty array means no availability.\n'
        '6. POST /api/v1/appointments/ with consultation_id and slot_id. General fee is INR 200. '
        'An appointment is reserved, not doctor-confirmed; pending reservations consume capacity.\n'
        '7. POST /api/v1/payments/orders/ with appointment_id and method (card/upi). '
        'Use returned order id, public key, amount in paise and currency with Razorpay mobile Checkout. '
        'Never submit card numbers, CVVs or UPI credentials to this API. Configure automatic capture in Razorpay.\n'
        '8. POST /api/v1/payments/verify/ with payment_id, razorpay_payment_id and razorpay_signature. '
        'Only gateway-confirmed captured payments succeed; signed webhooks also reconcile capture.\n'
        '9. Poll GET /api/v1/appointments/{id}/. Status moves awaiting_payment -> finding_doctor -> confirmed '
        'when staff assign a verified doctor. A 30-minute match or push notification is not implemented or guaranteed.\n\n'
        'All appointment summary prices are INR rupees; checkout order amounts are paise. '
        'Payment gateway configuration is required for live checkout. Private medical files must never be served '
        'through a public /media/ alias. Use PostgreSQL for production scheduling locks.'
    ),
    'VERSION': 'v1',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'ENUM_NAME_OVERRIDES': {
        'ConsultationStatusEnum': ['draft', 'requested', 'ongoing', 'completed', 'cancelled'],
        'AppointmentStatusEnum': ['pending', 'awaiting_payment', 'finding_doctor', 'confirmed', 'completed', 'cancelled'],
        'PaymentStatusEnum': ['pending', 'success', 'failed', 'refunded'],
        'ApplicationStatusEnum': [
            ('pending', 'Pending Review'), ('contacted', 'Contacted'),
            ('approved', 'Approved'), ('rejected', 'Rejected'),
        ],
    },
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}

# CORS - allow the Next.js frontend to call the API during development
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://127.0.0.1:3000',
    cast=Csv(),
)
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# TLS terminates at Nginx in production.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=False, cast=bool)


# Email
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET', default='')
RAZORPAY_WEBHOOK_SECRET = config('RAZORPAY_WEBHOOK_SECRET', default='')
