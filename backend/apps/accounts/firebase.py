import logging
import math
import os
import threading
import time

import firebase_admin
from django.conf import settings
from firebase_admin import auth, credentials, exceptions
from google.auth.exceptions import DefaultCredentialsError, GoogleAuthError
from rest_framework.exceptions import APIException, AuthenticationFailed

logger = logging.getLogger(__name__)
_app_lock = threading.Lock()


class AuthServiceUnavailable(APIException):
    status_code = 503
    default_detail = 'Authentication is temporarily unavailable. Please try again later.'
    default_code = 'auth_unavailable'


def firebase_app():
    if not settings.FIREBASE_PROJECT_ID or os.environ.get('FIREBASE_AUTH_EMULATOR_HOST'):
        raise AuthServiceUnavailable()
    with _app_lock:
        try:
            return firebase_admin.get_app('patient-auth')
        except ValueError:
            pass
        try:
            credential = (
                credentials.Certificate(settings.FIREBASE_CREDENTIALS_FILE)
                if settings.FIREBASE_CREDENTIALS_FILE else credentials.ApplicationDefault()
            )
            return firebase_admin.initialize_app(
                credential, {'projectId': settings.FIREBASE_PROJECT_ID, 'httpTimeout': 10},
                name='patient-auth',
            )
        except (ValueError, OSError, DefaultCredentialsError):
            logger.error('Firebase patient authentication credentials are not configured correctly.')
            raise AuthServiceUnavailable() from None


def verify_phone_token(id_token):
    app = firebase_app()
    try:
        claims = auth.verify_id_token(id_token, app=app, check_revoked=True)
    except (auth.InvalidIdTokenError, auth.RevokedIdTokenError, auth.UserDisabledError, auth.UserNotFoundError):
        raise AuthenticationFailed('Invalid, expired or revoked Firebase token. Sign in with your phone again.') from None
    except (exceptions.FirebaseError, GoogleAuthError, ValueError):
        logger.error('Firebase token verification service failed.')
        raise AuthServiceUnavailable() from None

    firebase = claims.get('firebase', {})
    authenticated_at = claims.get('auth_time')
    if (
        not isinstance(firebase, dict) or firebase.get('sign_in_provider') != 'phone' or firebase.get('tenant')
        or not isinstance(claims.get('uid'), str) or not claims['uid'] or len(claims['uid']) > 128
        or not isinstance(authenticated_at, (int, float)) or isinstance(authenticated_at, bool)
        or not math.isfinite(authenticated_at)
        or authenticated_at > time.time() + 30
        or time.time() - authenticated_at > settings.PATIENT_AUTH_RECENT_LOGIN_SECONDS
        or not isinstance(claims.get('exp'), (int, float)) or isinstance(claims['exp'], bool)
        or not math.isfinite(claims['exp']) or claims['exp'] <= time.time()
    ):
        raise AuthenticationFailed('A recent Firebase phone sign-in is required. Verify your phone OTP again.')
    return claims
