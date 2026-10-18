import re
from urllib.parse import parse_qs, urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator


def validate_public_url(value):
    URLValidator(schemes=['http', 'https'])(value)
    parsed = urlsplit(value)
    if parsed.username or parsed.password:
        raise ValidationError('Links must not contain usernames or passwords.')


def video_source(value):
    """Return a supported player URL without fetching or trusting embed HTML."""
    if not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
        return None
    host = (parsed.hostname or '').lower()
    parts = parsed.path.strip('/').split('/')
    video_id = ''
    if host in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtube-nocookie.com', 'www.youtube-nocookie.com'):
        if parsed.path == '/watch':
            video_id = parse_qs(parsed.query).get('v', [''])[0]
        elif len(parts) == 2 and parts[0] in ('shorts', 'embed', 'live'):
            video_id = parts[1]
    elif host in ('youtu.be', 'www.youtu.be') and len(parts) == 1:
        video_id = parts[0]
    if re.fullmatch(r'[A-Za-z0-9_-]{11}', video_id):
        return {'kind': 'embed', 'url': f'https://www.youtube-nocookie.com/embed/{video_id}?playsinline=1&rel=0'}
    if host in ('vimeo.com', 'www.vimeo.com') and len(parts) == 1 and re.fullmatch(r'[0-9]+', parts[0]):
        return {'kind': 'embed', 'url': f'https://player.vimeo.com/video/{parts[0]}'}
    if parsed.scheme == 'https' and parsed.path.lower().endswith('.mp4'):
        return {'kind': 'file', 'url': value}
    return None


def validate_video_url(value):
    validate_public_url(value)
    if video_source(value) is None:
        raise ValidationError('Use a YouTube video, public Vimeo video, or an HTTPS link ending in .mp4.')
