"""100ms server-only room provisioning and short-lived SDK authentication."""
import logging
import re
import time
import uuid

import jwt
import requests
from django.conf import settings
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)
API_URL = 'https://api.100ms.live/v2'
AUTH_TOKEN_SECONDS = 300


class VideoServiceUnavailable(APIException):
    status_code = 503
    default_detail = 'Video calling is temporarily unavailable. Please retry.'
    default_code = 'video_unavailable'


def configured_roles():
    roles = {'doctor': settings.HMS_DOCTOR_ROLE, 'patient': settings.HMS_PATIENT_ROLE}
    if (
        not settings.HMS_ACCESS_KEY or not settings.HMS_APP_SECRET
        or not valid_id(settings.HMS_TEMPLATE_ID)
        or any(not isinstance(role, str) or not role.strip() for role in roles.values())
        or roles['doctor'] == roles['patient']
    ):
        logger.error('100ms credentials, template or role configuration is missing or invalid.')
        raise VideoServiceUnavailable('100ms is not configured correctly on the server.')
    return roles


def valid_id(value):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value) is not None


def signed_token(token_type, ttl, **claims):
    now = int(time.time())
    try:
        token = jwt.encode({
            'access_key': settings.HMS_ACCESS_KEY, 'type': token_type, 'version': 2,
            'iat': now, 'nbf': now, 'exp': now + ttl, 'jti': str(uuid.uuid4()), **claims,
        }, settings.HMS_APP_SECRET, algorithm='HS256')
    except (jwt.PyJWTError, TypeError, ValueError):
        logger.error('100ms token signing failed.')
        raise VideoServiceUnavailable() from None
    return token, now + ttl


def request_json(method, path, **kwargs):
    management_token, _ = signed_token('management', 60)
    try:
        response = requests.request(
            method, f'{API_URL}{path}',
            headers={'Authorization': f'Bearer {management_token}'},
            timeout=10, allow_redirects=False, **kwargs,
        )
    except requests.RequestException:
        logger.error('100ms API request failed.')
        raise VideoServiceUnavailable() from None
    if not 200 <= response.status_code < 300:
        logger.error('100ms API returned HTTP %s.', response.status_code)
        raise VideoServiceUnavailable()
    try:
        return response.json()
    except ValueError:
        logger.error('100ms API returned invalid JSON.')
        raise VideoServiceUnavailable() from None


def validate_template(template_id, roles):
    template = request_json('GET', f'/templates/{template_id}')
    if not isinstance(template, dict) or template.get('id') != template_id:
        raise VideoServiceUnavailable('100ms returned an invalid template.')
    template_roles = template.get('roles')
    if not isinstance(template_roles, dict):
        raise VideoServiceUnavailable('100ms template roles are not configured correctly.')
    for role_name in roles.values():
        role = template_roles.get(role_name)
        permissions = role.get('permissions') if isinstance(role, dict) else None
        if (
            not isinstance(role, dict) or type(role.get('maxPeerCount')) is not int or role['maxPeerCount'] != 1
            or not isinstance(permissions, dict) or permissions.get('changeRole', False) is not False
            or any(permissions.get(key) is not False for key in ('browserRecording', 'rtmpStreaming', 'hlsStreaming'))
        ):
            raise VideoServiceUnavailable(
                'Configure both 100ms roles for one peer each, no role changes, and no recording or streaming permissions.',
            )
    destinations = template.get('destinations') or {}
    plugins = template.get('plugins') or {}
    template_settings = template.get('settings') or {}
    if not all(isinstance(value, dict) for value in (destinations, plugins, template_settings)):
        raise VideoServiceUnavailable('100ms returned invalid template settings.')
    recording = template_settings.get('recording') or {}
    browser_recordings = destinations.get('browserRecordings') or []
    if (
        not isinstance(recording, dict) or not isinstance(browser_recordings, list)
        or any(not isinstance(item, dict) for item in browser_recordings)
        or destinations.get('transcriptions') or plugins.get('transcriptions') or recording.get('enabled')
        or any(item.get('autoStart') for item in browser_recordings)
    ):
        raise VideoServiceUnavailable('Disable automatic recording and transcription in the 100ms template.')


def checked_room(room, reservation):
    if (
        not isinstance(room, dict) or not valid_id(room.get('id'))
        or not isinstance(room.get('name'), str) or room['name'].lower() != reservation.room_name
        or room.get('template_id') != reservation.template_id or room.get('enabled') is not True
        or not isinstance(room.get('recording_info'), dict) or room['recording_info'].get('enabled') is not False
    ):
        raise VideoServiceUnavailable('The 100ms room is disabled or its configuration is invalid.')
    return room['id']


def retrieve_room(room_id, reservation):
    returned_id = checked_room(request_json('GET', f'/rooms/{room_id}'), reservation)
    if returned_id != room_id:
        raise VideoServiceUnavailable('100ms returned a different room. Contact support.')
    return returned_id


def provision_room(reservation):
    if reservation.room_id:
        return retrieve_room(reservation.room_id, reservation)
    # The reservation name is committed before any remote request, including one that times out.
    for enabled in ('true', 'false'):
        result = request_json('GET', '/rooms', params={'name': reservation.room_name, 'enabled': enabled, 'limit': 10})
        # 100ms omits "data" (or sends null) when no room matches the name.
        rooms = result.get('data') if isinstance(result, dict) else None
        if rooms is None and isinstance(result, dict):
            rooms = []
        if not isinstance(rooms, list):
            logger.error('100ms room list had an unexpected shape: %s.', type(result).__name__)
            raise VideoServiceUnavailable('100ms returned an invalid room list.')
        matches = [
            room for room in rooms
            if isinstance(room, dict) and isinstance(room.get('name'), str) and room['name'].lower() == reservation.room_name
        ]
        if len(matches) > 1:
            raise VideoServiceUnavailable('100ms returned conflicting rooms. Contact support.')
        if matches:
            room_id = matches[0].get('id')
            if not valid_id(room_id):
                raise VideoServiceUnavailable('100ms returned an invalid room identifier.')
            return retrieve_room(room_id, reservation)
    result = request_json('POST', '/rooms', json={
        'name': reservation.room_name, 'template_id': reservation.template_id,
        'recording_info': {'enabled': False},
    })
    room_id = result.get('id') if isinstance(result, dict) else result
    if not valid_id(room_id):
        raise VideoServiceUnavailable('100ms returned an invalid room identifier.')
    return retrieve_room(room_id, reservation)
