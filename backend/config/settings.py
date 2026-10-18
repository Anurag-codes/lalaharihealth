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
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    # LalahariHealth apps
    'apps.core',
    'apps.blogs',
    'apps.accounts',
    'apps.doctors',
    'apps.patients',
    'apps.treatments',
    'apps.hospitals',
    'apps.consultations',
    'apps.appointments',
    'apps.payments',
    'apps.notifications',
    'apps.pricing',
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
        '1. Request and verify Gmail email OTP through /api/v1/auth/patient/email/request-otp/ '
        'and /api/v1/auth/patient/email/verify-otp/, or verify phone OTP in the app with Firebase '
        'and exchange its ID token at /api/v1/auth/patient/phone/firebase/. New verified patients '
        'are registered automatically. Use the returned access JWT as a Bearer token. Refresh '
        'through /api/v1/auth/patient/token/refresh/. Signed-in patients can link another verified '
        'contact through /api/v1/auth/patient/link/. Legacy password endpoints remain available.\n'
        'Logged-out users fill Patient Details first, then log in with phone OTP, then continue at step 2.\n'
        '2. Select Patient: GET /api/v1/patients/booking-patients/ lists Myself and family members '
        '(add one with POST /api/v1/patients/family-members/). POST /api/v1/consultations/ with family_member_id '
        '(null = Myself), mode and, for Book Specialist, speciality (id from GET /api/v1/doctors/specialities/); blank patient fields are auto-filled. A 400 listing missing fields means show '
        'the Patient Details form and send patient_name, patient_age, patient_gender and patient_phone.\n'
        '3. Symptoms: GET /api/v1/consultations/conditions/ returns disease -> type -> variant. '
        'PUT /api/v1/consultations/{id}/history/ with condition, condition_type and condition_variant '
        '(required when that level has options), condition_details, duration_value, duration_unit, '
        'ongoing_medication and treatment_details.\n'
        '4. Optional POST /api/v1/consultations/{id}/documents/ as multipart with one file per request. '
        'PDF/PNG/JPG up to 10 MB. Skip means no upload call; private downloads require authentication.\n'
        '5. Schedule Appointment: GET /api/v1/appointments/slot-dates/?days=7 for the date strip and '
        'GET /api/v1/appointments/slots/?date=YYYY-MM-DD (add speciality_id= for specialists) for 15-minute times (Asia/Kolkata, 08:00-23:59) '
        'opened by verified doctors through /api/v1/doctors/me/slots/. "Request Appointment" reserves nothing.\n'
        '6. Case Preview: GET /api/v1/consultations/{id}/preview/?slot_id=. "Submit Case": POST /api/v1/appointments/ '
        'with consultation_id, slot_id and information_confirmed=true. General fee is the country rate from the pricing table (default India INR 200) using the country_code sent in step 1; specialists always use the INR speciality fee. '
        'An appointment is reserved, not doctor-confirmed; pending reservations consume the slot.\n'
        '7. Checkout: POST /api/v1/payments/orders/ with appointment_id and method (card/upi). '
        'Use returned order id, public key, amount in minor units of the currency (paise, cents...) and currency with Razorpay mobile Checkout. '
        'Never submit card numbers, CVVs or UPI credentials to this API. Configure automatic capture in Razorpay.\n'
        '8. POST /api/v1/payments/verify/ with payment_id, razorpay_payment_id and razorpay_signature. '
        'Only gateway-confirmed captured payments succeed; signed webhooks also reconcile capture.\n'
        '9. Finding Your Doctor: poll GET /api/v1/appointments/{id}/. Status moves awaiting_payment -> finding_doctor '
        '-> confirmed when staff assign a verified doctor of that speciality. The 30-minute match is a staff target, not guaranteed. '
        'Each change also creates a notification and an FCM push.\n\n'
        'Location pricing: GET /api/v1/pricing/?lat=&lng= (or ?country=US) is public and returns the general physician fee for the country of the user, falling back to India INR 200 when the country has no active rate. Send its country_code in booking step 1. Appointment summary prices are whole units of the appointment currency; checkout order amounts are minor units. '
        'Payment gateway configuration is required for live checkout. Private medical files must never be served '
        'through a public /media/ alias. Use PostgreSQL for production scheduling locks.\n\n'
        'Profile section: GET/PATCH /api/v1/patients/profile/ (name, city, gender, date of birth, app language en/hi), '
        'PUT/DELETE /api/v1/patients/profile/photo/, family CRUD at /api/v1/patients/family-members/, '
        'Medical Records at /api/v1/patients/medical-records/ and /{id}/, and Contact Us at '
        '/api/v1/core/support-contacts/. Verified doctors write diagnosis and prescriptions through '
        '/api/v1/doctors/me/consultations/{id}/record/.\n\n'
        'Home screen: GET /api/v1/patients/home/ (name, photo, language, bell count, General Physician card, '
        'specialities, support number, upcoming appointments, My Cases badge). My Cases with a progress tracker: '
        'GET /api/v1/patients/cases/?status=active|closed and /{consultation_id}/. Notifications: '
        'GET /api/v1/notifications/, unread-count/, {id}/read/, read-all/; register the FCM token after login with '
        'POST /api/v1/notifications/devices/ and remove it on logout with devices/remove/.\n\n'
        'Conventions: JSON bodies (multipart only for file uploads). Lists are paginated as '
        '{count, next, previous, results} with ?page=. Errors use HTTP status codes with a JSON body: '
        '{"detail": "message"} or {"field": ["message"]} for validation (400). 401 = refresh the token or log in, '
        '403 = not allowed, 404 = not found or not yours, 429 = too many requests, 503 = service not configured. '
        'Every endpoint below shows request and response examples and its error responses.'
    ),
    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.hooks.postprocess_schema_enums',
        'apps.core.openapi.add_docs',
    ],
    'VERSION': 'v1',
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'ENUM_NAME_OVERRIDES': {
        'VerifiedIdentityKindEnum': [('email', 'Email'), ('phone', 'Phone')],
        'BlogPostKindEnum': [('external', 'External blog / video link'), ('article', 'Original article')],
        'BlogBlockKindEnum': [('heading', 'Heading'), ('paragraph', 'Paragraph'), ('image', 'Image'), ('video', 'Video link')],
        'BlogVideoKindEnum': ['embed', 'file'],
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
    'BLACKLIST_AFTER_ROTATION': True,
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

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default=EMAIL_HOST_USER)
EMAIL_TIMEOUT = 10

EMAIL_OTP_EXPIRY_SECONDS = 300
EMAIL_OTP_RESEND_SECONDS = 60
EMAIL_OTP_MAX_ATTEMPTS = 5
EMAIL_OTP_ADDRESS_HOURLY_LIMIT = 5
EMAIL_OTP_IP_HOURLY_LIMIT = 20
PATIENT_AUTH_VERIFY_HOURLY_LIMIT = 60
PATIENT_AUTH_RECENT_LOGIN_SECONDS = 300
PATIENT_AUTH_TRUST_PROXY_HEADERS = config('PATIENT_AUTH_TRUST_PROXY_HEADERS', default=False, cast=bool)
FIREBASE_PROJECT_ID = config('FIREBASE_PROJECT_ID', default='')
FIREBASE_CREDENTIALS_FILE = config('FIREBASE_CREDENTIALS_FILE', default='')

SUPPORT_PHONE_NUMBER = config('SUPPORT_PHONE_NUMBER', default='+919818677599')
SUPPORT_EMAIL = config('SUPPORT_EMAIL', default='care@lalaharihealth.com')

# Shown to patients ("Matched within 30 minutes"); matching itself is done by staff.
DOCTOR_MATCH_TARGET_MINUTES = config('DOCTOR_MATCH_TARGET_MINUTES', default=30, cast=int)
# Push uses Firebase Cloud Messaging with the FIREBASE_* credentials above; skipped when they are not set.
PUSH_NOTIFICATIONS_ENABLED = config('PUSH_NOTIFICATIONS_ENABLED', default=True, cast=bool)
APPOINTMENT_REMINDER_MINUTES = config('APPOINTMENT_REMINDER_MINUTES', default=30, cast=int)

RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET', default='')
RAZORPAY_WEBHOOK_SECRET = config('RAZORPAY_WEBHOOK_SECRET', default='')
