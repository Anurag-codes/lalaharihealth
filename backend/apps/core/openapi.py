"""drf-spectacular postprocessing hook that completes the schema for app developers.

Adds descriptions, request/response examples (from openapi_examples.json, captured from
real API responses) and documented error responses to every operation, without
overwriting anything a view already declares with extend_schema.
"""

import copy
import json
import re
from pathlib import Path

EXAMPLES = json.loads((Path(__file__).with_name('openapi_examples.json')).read_text(encoding='utf-8'))

AUTH = 'Send `Authorization: Bearer <access>` (access JWT from login).'

DESCRIPTIONS = {
    'POST /api/v1/auth/patient/email/request-otp/': (
        'Login/sign-up step 1 (email). Sends a 6-digit OTP from our Gmail account to the email. '
        'Returns 202 even for new emails; nothing is created yet. Resend after the cooldown, otherwise 429. '
        '503 means email sending is not configured on the server.'
    ),
    'POST /api/v1/auth/patient/email/verify-otp/': (
        'Login/sign-up step 2 (email). Send the `request_id` returned by request-otp/ and the 6-digit OTP. A new email is registered '
        'as a patient automatically (`is_new_user: true`, show the name/onboarding screen); an existing '
        'patient is signed in (`is_new_user: false`). Store `access` (60 minutes) and `refresh` (7 days) securely. '
        'Too many wrong codes give 429; a non-patient account gives 403.'
    ),
    'POST /api/v1/auth/patient/link/email/request-otp/': (
        'Signed-in patient adds an email to the account (for example after phone login). Sends an OTP to the new email. ' + AUTH
    ),
    'POST /api/v1/auth/patient/link/email/verify-otp/': (
        'Send the `request_id` from link/email/request-otp/ with the OTP to attach the email to the signed-in patient. '
        '400 if the code is wrong or the email belongs to another account. ' + AUTH
    ),
    'POST /api/v1/auth/patient/logout/': (
        'Logout. Send the current refresh token; it is blacklisted so it can no longer be used. '
        'Also call POST /api/v1/notifications/devices/remove/ before this, then delete stored tokens. Returns 204. ' + AUTH
    ),
    'GET /api/v1/auth/patient/me/': 'Signed-in patient account: name, city, verified email/phone and linked identities. ' + AUTH,
    'PATCH /api/v1/auth/patient/me/': (
        'Update first_name, last_name and city (use after `is_new_user: true`). Email, phone, role and '
        'verification flags cannot be changed here (400); use the link endpoints. ' + AUTH
    ),
    'GET /api/v1/blogs/': (
        'Public. Published blogs, newest first, paginated (20 per page, use `?page=`). `kind` is `external` '
        '(a link to another blog or YouTube video) or `article` (our own blog). Open GET /api/v1/blogs/{slug}/ for details.'
    ),
    'GET /api/v1/blogs/{slug}/': (
        'Public. One published blog. For `external`, open `source_url` (or play `source_video`). For `article`, render `blocks` in order: heading, paragraph, image '
        '(with caption) or video (`video_kind` embed URL or uploaded file). 404 for unknown or unpublished slugs.'
    ),
    'GET /api/v1/consultations/': 'Your consultations (drafts and booked), newest first, paginated with `?page=`. ' + AUTH,
    'GET /api/v1/consultations/{consultation_id}/': 'One of your consultations with patient details and symptom history. 404 if it is not yours. ' + AUTH,
    'PATCH /api/v1/consultations/{consultation_id}/': (
        'Booking step 1 correction: change the patient (family_member_id), patient details, speciality, '
        'mode or country_code before the appointment is submitted. Send only changed fields. ' + AUTH
    ),
    'GET /api/v1/consultations/{consultation_id}/documents/': 'Reports uploaded for this consultation (paginated). Use `download_url` with the auth header to open a file. ' + AUTH,
    'POST /api/v1/consultations/{consultation_id}/documents/': (
        'Booking step 4 (optional). multipart/form-data with field `file`: one PDF/PNG/JPG up to 10 MB per request; '
        'call again for more files. ' + AUTH
    ),
    'DELETE /api/v1/consultations/{consultation_id}/documents/{document_id}/': 'Remove an uploaded report before submitting the case. Returns 204. ' + AUTH,
    'GET /api/v1/consultations/{consultation_id}/documents/{document_id}/download/': (
        'Streams the private file (PDF/image bytes) for the owner or the assigned doctor. Files are never public. ' + AUTH
    ),
    'GET /api/v1/doctors/me/consultations/{consultation_id}/record/': (
        'Doctor app: patient intake (details, symptoms, documents) and the current diagnosis/prescription record '
        'for a consultation assigned to you. 403 for non-doctors, 404 if not assigned. ' + AUTH
    ),
    'GET /api/v1/doctors/me/slots/': 'Doctor app: your 15-minute slots for the required `?date=YYYY-MM-DD`, with booked flags. Verified doctors only (403 otherwise). ' + AUTH,
    'GET /api/v1/health/': 'Public liveness check. Returns 200 when the API is up.',
    'POST /api/v1/notifications/{notification_id}/read/': 'Mark one notification as read (on tap). Returns the updated notification. ' + AUTH,
    'POST /api/v1/notifications/devices/remove/': 'Unregister this device FCM token so it stops receiving pushes. Call on logout. Returns 204. ' + AUTH,
    'POST /api/v1/notifications/read-all/': 'Mark all your notifications as read; returns how many were updated. ' + AUTH,
    'GET /api/v1/notifications/unread-count/': 'Number for the red dot on the bell icon. ' + AUTH,
    'GET /api/v1/patients/cases/{consultation_id}/': 'My Cases detail: one case with appointment, doctor and progress tracker steps. ' + AUTH,
    'GET /api/v1/patients/family-members/': 'Family members linked to your account (Profile > Family). ' + AUTH,
    'GET /api/v1/patients/family-members/{member_id}/': 'One family member. 404 if it is not yours. ' + AUTH,
    'GET /api/v1/patients/profile/': 'Profile screen: name, photo, phone, email, gender, date of birth, city and app language. ' + AUTH,
    'DELETE /api/v1/patients/profile/photo/': 'Remove your profile photo. Returns 204. ' + AUTH,
    'GET /api/v1/payments/{payment_id}/': 'Status of one of your payments (pending, success, failed, refunded). ' + AUTH,
    'GET /api/v1/appointments/': 'My appointments, newest first, paginated with `?page=`. Each has status, slot time, doctor and fee. ' + AUTH,
    'POST /api/v1/auth/token/': 'Legacy username/password login (staff and doctors). Patients should use OTP login.',
    'POST /api/v1/auth/token/refresh/': 'Legacy refresh for password logins. Patients use /api/v1/auth/patient/token/refresh/.',
}

STATUS_TEXT = {
    '400': 'Validation error. Body maps each invalid field to a list of messages, or has `detail`.',
    '401': 'Missing, invalid or expired access token. Refresh the token and retry, or log in again.',
    '403': 'Signed in, but not allowed (wrong role or account).',
    '404': 'Not found, or it does not belong to you.',
    '429': 'Too many requests. Wait and retry.',
    '503': 'Service is not configured or temporarily unavailable on the server.',
}

DEFAULT_ERRORS = {
    '400': {'field_name': ['This field is required.']},
    '401': {'detail': 'Authentication credentials were not provided.'},
    '404': {'detail': 'Not found.'},
}

ERROR_SCHEMA = {
    'description': (
        'Error body: `{"detail": "message"}` (JWT errors add `code`), `{"field": ["message"]}` '
        'for invalid fields, or `["message"]` for a general validation error.'
    ),
    'oneOf': [
        {
            'type': 'object',
            'properties': {'detail': {'type': 'string'}, 'code': {'type': 'string'}},
            'additionalProperties': True,
        },
        {'type': 'array', 'items': {'type': 'string'}},
    ],
}


def _has_examples(media):
    return bool(media.get('examples') or 'example' in media)


def _requires_auth(op):
    security = op.get('security')
    return bool(security) and {} not in security


def _takes_input(op):
    params = [p for p in op.get('parameters', []) if p.get('in') == 'query' and p['name'] != 'page']
    return 'requestBody' in op or bool(params)


def _example(value, summary='Example'):
    return {summary: {'value': copy.deepcopy(value)}}


def _unwrap_list_examples(media):
    """drf-spectacular wraps examples of list/paginated responses; undo it when the
    hand-written example already is a full list or page, so Swagger shows it once."""
    schema_type = media.get('schema', {}).get('type')
    for example in media.get('examples', {}).values():
        value = example.get('value')
        if schema_type == 'array' and isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
            example['value'] = value[0]
        elif isinstance(value, dict) and isinstance(value.get('results'), list) and len(value['results']) == 1:
            inner = value['results'][0]
            if isinstance(inner, dict) and {'count', 'results'} <= inner.keys():
                example['value'] = inner


def add_docs(result, generator, request, public):
    result.setdefault('components', {}).setdefault('schemas', {})['Error'] = ERROR_SCHEMA
    error_ref = {'$ref': '#/components/schemas/Error'}

    for path, methods in result.get('paths', {}).items():
        for method, op in methods.items():
            key = f'{method.upper()} {path}'
            data = EXAMPLES.get(key, {})

            if not op.get('description') and key in DESCRIPTIONS:
                op['description'] = DESCRIPTIONS[key]

            if 'request' in data and 'requestBody' in op:
                for media in op['requestBody'].get('content', {}).values():
                    if not _has_examples(media):
                        media['examples'] = _example(data['request'])

            responses = op.setdefault('responses', {})
            status = str(data.get('status', ''))
            success = [code for code in responses if code.startswith('2')]
            if status and status not in responses and len(success) == 1:
                responses[status] = responses.pop(success[0])
            for response in responses.values():
                for media in response.get('content', {}).values():
                    _unwrap_list_examples(media)
            if 'response' in data and status in responses:
                for content_type, media in responses[status].get('content', {}).items():
                    if content_type.endswith('json') and not _has_examples(media):
                        media['examples'] = _example(data['response'])

            errors = dict(data.get('errors', {}))
            if _requires_auth(op):
                errors.setdefault('401', DEFAULT_ERRORS['401'])
            if '{' in path:
                errors.setdefault('404', DEFAULT_ERRORS['404'])
            if _takes_input(op):
                errors.setdefault('400', DEFAULT_ERRORS['400'])
            for code in sorted(errors):
                response = responses.setdefault(code, {'description': STATUS_TEXT.get(code, 'Error')})
                if not response.get('description'):
                    response['description'] = STATUS_TEXT.get(code, 'Error')
                content = response.setdefault('content', {})
                media = content.setdefault('application/json', {'schema': error_ref})
                if not _has_examples(media):
                    media['examples'] = _example(errors[code], 'Error')

            # keep response codes in numeric order for Swagger UI
            op['responses'] = dict(sorted(responses.items(), key=lambda item: re.sub(r'\D', '9', item[0])))
    return result
