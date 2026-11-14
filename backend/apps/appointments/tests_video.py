import copy
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

import jwt
import requests
from django.db import close_old_connections, connections
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.consultations.models import Consultation
from apps.doctors.models import DoctorProfile
from .hms import AUTH_TOKEN_SECONDS, VideoServiceUnavailable, checked_room, configured_roles, signed_token, validate_template
from .models import Appointment, AppointmentCall, AppointmentVideoRoom

HMS_SETTINGS = {
    'HMS_ACCESS_KEY': 'test-access-key', 'HMS_APP_SECRET': 'test-signing-secret-not-a-live-credential',
    'HMS_TEMPLATE_ID': 'template-test', 'HMS_DOCTOR_ROLE': 'doctor', 'HMS_PATIENT_ROLE': 'patient',
    'PASSWORD_HASHERS': ['django.contrib.auth.hashers.MD5PasswordHasher'],
}


def template():
    return {
        'id': 'template-test', 'roles': {
            name: {
                'maxPeerCount': 1,
                'permissions': {
                    'changeRole': False, 'browserRecording': False, 'rtmpStreaming': False, 'hlsStreaming': False,
                },
            } for name in ('doctor', 'patient')
        },
        'settings': {'recording': None}, 'destinations': {},
    }


class Fake100ms:
    def __init__(self):
        self.rooms = {}
        self.creations = 0
        self.requests = []
        self.lock = threading.Lock()
        self.timeout_after_create = False

    def request(self, method, url, **kwargs):
        management = jwt.decode(kwargs['headers']['Authorization'].split()[1], HMS_SETTINGS['HMS_APP_SECRET'], algorithms=['HS256'])
        if management['type'] != 'management' or management['exp'] - management['iat'] != 60:
            raise AssertionError('Invalid management token.')
        if kwargs['allow_redirects'] is not False:
            raise AssertionError('Management credentials must not follow redirects.')
        with self.lock:
            self.requests.append((method, url, kwargs))
            if url.endswith('/templates/template-test'):
                data = template()
            elif method == 'POST' and url.endswith('/rooms'):
                body = kwargs['json']
                name = body['name']
                if name not in self.rooms:
                    self.creations += 1
                    self.rooms[name] = {
                        'id': f'room-{self.creations}', 'name': name, 'template_id': body['template_id'],
                        'enabled': True, 'recording_info': body['recording_info'],
                    }
                time.sleep(0.05)
                if self.timeout_after_create:
                    self.timeout_after_create = False
                    raise requests.Timeout('Simulated lost response.')
                data = self.rooms[name]
            elif method == 'GET' and url.endswith('/rooms'):
                params = kwargs['params']
                data = {'data': [
                    room for room in self.rooms.values()
                    if room['name'] == params['name'] and str(room['enabled']).lower() == params['enabled']
                ]}
            else:
                data = next(room for room in self.rooms.values() if url.endswith(f'/rooms/{room["id"]}'))
            return SimpleNamespace(status_code=200, json=lambda: copy.deepcopy(data))


class VideoFixtures:
    def setUp(self):
        super().setUp()
        self.patient = User.objects.create_user(username='video_patient', role='patient')
        self.doctor = User.objects.create_user(username='video_doctor', role='doctor')
        DoctorProfile.objects.create(user=self.doctor, verification_status='verified')
        self.appointment = self.make_appointment(self.patient, self.doctor)
        self.provider = Fake100ms()
        provider_patch = patch('apps.appointments.hms.requests.request', side_effect=self.provider.request)
        provider_patch.start()
        self.addCleanup(provider_patch.stop)

    def make_appointment(self, patient, doctor):
        consultation = Consultation.objects.create(
            patient=patient, doctor=doctor, mode='video', status='requested',
        )
        return Appointment.objects.create(
            patient=patient, doctor=doctor, consultation=consultation,
            status='confirmed', slot_time=timezone.now(), paid_at=timezone.now(),
        )

    def join(self, user, appointment=None, body=None):
        appointment = appointment or self.appointment
        client = APIClient()
        client.force_authenticate(user)
        prefix = '/api/v1/doctors/me/appointments/' if user.role == 'doctor' else '/api/v1/appointments/'
        return client.post(f'{prefix}{appointment.pk}/video/join/', body if body is not None else {}, format='json')


@override_settings(**HMS_SETTINGS)
@skipUnlessDBFeature('has_select_for_update')
class VideoJoinTests(VideoFixtures, TestCase):
    def test_role_tokens_and_reconnects_reuse_room_without_starting_call(self):
        doctor = self.join(self.doctor)
        patient = self.join(self.patient)
        reconnect = self.join(self.doctor)
        for response, user, role in ((doctor, self.doctor, 'doctor'), (patient, self.patient, 'patient'), (reconnect, self.doctor, 'doctor')):
            self.assertEqual(response.status_code, 200, response.data)
            self.assertIn('no-store', response['Cache-Control'])
            claims = jwt.decode(response.data['auth_token'], HMS_SETTINGS['HMS_APP_SECRET'], algorithms=['HS256'])
            self.assertEqual(claims['type'], 'app')
            self.assertEqual(claims['version'], 2)
            self.assertEqual(claims['access_key'], HMS_SETTINGS['HMS_ACCESS_KEY'])
            self.assertEqual(claims['role'], role)
            self.assertEqual(claims['user_id'], f'user-{user.pk}')
            self.assertEqual(claims['room_id'], response.data['room_id'])
            self.assertEqual(claims['exp'] - claims['iat'], AUTH_TOKEN_SECONDS)
            self.assertEqual(response.data['expires_in'], AUTH_TOKEN_SECONDS)
            self.assertNotIn(HMS_SETTINGS['HMS_APP_SECRET'], str(response.data))
            self.assertNotIn('management_token', response.data)
        self.assertEqual(doctor.data['room_id'], patient.data['room_id'])
        self.assertEqual(doctor.data['call_id'], reconnect.data['call_id'])
        self.assertNotEqual(doctor.data['auth_token'], reconnect.data['auth_token'])
        self.assertEqual(self.provider.creations, 1)
        self.assertEqual(AppointmentCall.objects.count(), 1)
        call = AppointmentCall.objects.get()
        self.assertEqual(call.status, 'unknown')
        self.assertIsNone(call.started_at)
        self.assertIsNone(call.ended_at)
        self.assertEqual(next(iter(self.provider.rooms.values()))['recording_info'], {'enabled': False})

    def test_join_authorization_and_appointment_restrictions(self):
        client = APIClient()
        path = f'/api/v1/appointments/{self.appointment.pk}/video/join/'
        self.assertEqual(client.post(path, {}, format='json').status_code, 401)
        other = User.objects.create_user(username='other_patient', role='patient')
        self.assertEqual(self.join(other).status_code, 404)
        other_doctor = User.objects.create_user(username='other_doctor', role='doctor')
        DoctorProfile.objects.create(user=other_doctor, verification_status='verified')
        self.assertEqual(self.join(other_doctor).status_code, 404)
        client.force_authenticate(self.doctor)
        self.assertEqual(client.post(path, {}, format='json').status_code, 403)
        client.force_authenticate(self.patient)
        self.assertEqual(client.post(
            f'/api/v1/doctors/me/appointments/{self.appointment.pk}/video/join/', {}, format='json',
        ).status_code, 403)
        self.assertEqual(self.join(self.patient, body={'role': 'doctor', 'room_id': 'another'}).status_code, 400)
        for status in ('pending', 'awaiting_payment', 'finding_doctor', 'completed', 'cancelled'):
            Appointment.objects.filter(pk=self.appointment.pk).update(status=status)
            with self.subTest(status=status):
                self.assertEqual(self.join(self.patient).status_code, 400)
        Appointment.objects.filter(pk=self.appointment.pk).update(status='confirmed')
        for mode in ('chat', 'audio'):
            Consultation.objects.filter(pk=self.appointment.consultation_id).update(mode=mode)
            self.assertEqual(self.join(self.patient).status_code, 400)
        Consultation.objects.filter(pk=self.appointment.consultation_id).update(mode='video', status='completed')
        self.assertEqual(self.join(self.patient).status_code, 400)
        Consultation.objects.filter(pk=self.appointment.consultation_id).update(status='requested')
        Appointment.objects.filter(pk=self.appointment.pk).update(slot_time=timezone.now() + timedelta(minutes=6))
        self.assertEqual(self.join(self.patient).status_code, 400)
        now = timezone.now()
        Appointment.objects.filter(pk=self.appointment.pk).update(slot_time=now + timedelta(minutes=5))
        with patch('apps.appointments.video_calls.timezone.now', return_value=now):
            self.assertEqual(self.join(self.patient).status_code, 200)
        DoctorProfile.objects.filter(user=self.doctor).update(verification_status='pending')
        self.assertEqual(self.join(self.doctor).status_code, 403)
        self.assertEqual(self.join(self.patient).status_code, 400)
        DoctorProfile.objects.filter(user=self.doctor).update(verification_status='verified')
        User.objects.filter(pk=self.patient.pk).update(is_active=False)
        self.assertEqual(self.join(self.doctor).status_code, 400)

    def test_provider_timeout_adopts_same_room_on_retry(self):
        self.provider.timeout_after_create = True
        first = self.join(self.doctor)
        self.assertEqual(first.status_code, 503, first.data)
        reservation = AppointmentVideoRoom.objects.get()
        self.assertIsNone(reservation.room_id)
        self.assertEqual(AppointmentCall.objects.count(), 0)
        second = self.join(self.patient)
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(self.provider.creations, 1)
        reservation.refresh_from_db()
        self.assertEqual(reservation.room_id, second.data['room_id'])
        self.assertEqual(next(iter(self.provider.rooms)), reservation.room_name)

    def test_provider_errors_disabled_rooms_and_missing_configuration(self):
        with override_settings(HMS_APP_SECRET=''):
            self.assertEqual(self.join(self.doctor).status_code, 503)
        self.assertEqual(len(self.provider.requests), 0)
        with patch('apps.appointments.hms.requests.request', return_value=SimpleNamespace(status_code=429)):
            self.assertEqual(self.join(self.patient).status_code, 503)
        with patch('apps.appointments.hms.requests.request', return_value=SimpleNamespace(status_code=200, json=lambda: [])):
            self.assertEqual(self.join(self.patient).status_code, 503)
        joined = self.join(self.doctor)
        self.assertEqual(joined.status_code, 200, joined.data)
        next(iter(self.provider.rooms.values()))['enabled'] = False
        self.assertEqual(self.join(self.patient).status_code, 503)
        self.assertEqual(self.provider.creations, 1)

    def test_sdk_callbacks_use_managed_record_and_remain_separate_from_completion(self):
        joined = self.join(self.doctor)
        self.assertEqual(joined.status_code, 200, joined.data)
        client = APIClient()
        client.force_authenticate(self.doctor)
        prefix = f'/api/v1/doctors/me/appointments/{self.appointment.pk}/calls/'
        call_url = f'{prefix}{joined.data["call_id"]}/'
        started = timezone.now()
        payload = {'status': 'in_progress', 'started_at': started.isoformat()}
        for _ in range(2):
            self.assertEqual(client.patch(call_url, payload, format='json').status_code, 200)
            self.assertEqual(self.join(self.patient).data['call_id'], joined.data['call_id'])
        self.assertEqual(client.post(prefix, {
            'provider': '100ms', 'external_call_id': joined.data['room_id'],
        }, format='json').status_code, 400)
        self.assertEqual(client.patch(call_url, {'external_call_id': 'another-room'}, format='json').status_code, 400)
        self.assertEqual(client.patch(call_url, {'provider': 'zoho_meeting'}, format='json').status_code, 400)
        ended = {'status': 'failed', 'ended_at': (started + timedelta(seconds=30)).isoformat(), 'end_reason': 'final_sdk_failure'}
        for _ in range(2):
            self.assertEqual(client.patch(call_url, ended, format='json').status_code, 200)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'confirmed')
        self.assertIsNone(self.appointment.completed_at)
        retry = self.join(self.doctor)
        self.assertEqual(retry.data['room_id'], joined.data['room_id'])
        self.assertNotEqual(retry.data['call_id'], joined.data['call_id'])
        self.assertEqual(self.join(self.patient).data['call_id'], retry.data['call_id'])
        self.assertEqual(AppointmentCall.objects.count(), 2)


@override_settings(**HMS_SETTINGS)
@skipUnlessDBFeature('has_select_for_update')
class VideoConcurrencyTests(VideoFixtures, TransactionTestCase):
    def threaded_join(self, user, appointment, barrier):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            response = self.join(user, appointment)
            return response.status_code, response.data
        finally:
            connections.close_all()

    def test_concurrent_doctor_patient_and_reconnect_share_one_room_and_call(self):
        barrier = threading.Barrier(4)
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(self.threaded_join, user, self.appointment, barrier)
                for user in (self.doctor, self.patient, self.doctor, self.patient)
            ]
            results = [future.result(timeout=30) for future in futures]
        self.assertTrue(all(status == 200 for status, _ in results), results)
        self.assertEqual(len({data['room_id'] for _, data in results}), 1)
        self.assertEqual(len({data['call_id'] for _, data in results}), 1)
        self.assertEqual(AppointmentVideoRoom.objects.count(), 1)
        self.assertEqual(AppointmentCall.objects.count(), 1)
        self.assertEqual(self.provider.creations, 1)

    def test_five_simultaneous_consultations_get_distinct_rooms(self):
        appointments = [(self.patient, self.doctor, self.appointment)]
        for index in range(1, 5):
            patient = User.objects.create_user(username=f'patient-{index}', role='patient')
            doctor = User.objects.create_user(username=f'doctor-{index}', role='doctor')
            DoctorProfile.objects.create(user=doctor, verification_status='verified')
            appointments.append((patient, doctor, self.make_appointment(patient, doctor)))
        barrier = threading.Barrier(10)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(self.threaded_join, user, appointment, barrier)
                for patient, doctor, appointment in appointments for user in (patient, doctor)
            ]
            results = [future.result(timeout=30) for future in futures]
        self.assertTrue(all(status == 200 for status, _ in results), results)
        self.assertEqual(len({data['room_id'] for _, data in results}), 5)
        self.assertEqual(self.provider.creations, 5)
        self.assertEqual(AppointmentCall.objects.count(), 5)


@override_settings(**HMS_SETTINGS)
class VideoProviderTests(SimpleTestCase):
    def test_short_lived_token_rejects_wrong_secret_and_expiry(self):
        token, expires = signed_token('app', AUTH_TOKEN_SECONDS, room_id='room-test', role='doctor', user_id='user-1')
        with self.assertRaises(jwt.InvalidSignatureError):
            jwt.decode(token, 'wrong-test-secret', algorithms=['HS256'])
        with patch('apps.appointments.hms.time.time', return_value=time.time() - AUTH_TOKEN_SECONDS - 1):
            expired, _ = signed_token('app', AUTH_TOKEN_SECONDS, room_id='room-test', role='patient', user_id='user-2')
        with self.assertRaises(jwt.ExpiredSignatureError):
            jwt.decode(expired, HMS_SETTINGS['HMS_APP_SECRET'], algorithms=['HS256'])
        self.assertGreater(expires, time.time())

    def test_unsafe_template_permissions_peer_counts_and_transcription_fail_closed(self):
        bad_templates = []
        for field, value in (('maxPeerCount', 0), ('maxPeerCount', True)):
            value_template = template()
            value_template['roles']['patient'][field] = value
            bad_templates.append(value_template)
        for key in ('changeRole', 'browserRecording'):
            value_template = template()
            value_template['roles']['patient']['permissions'][key] = True
            bad_templates.append(value_template)
        value_template = template()
        value_template['destinations'] = {'transcriptions': {'medical-notes': {}}}
        bad_templates.append(value_template)
        value_template = template()
        value_template['settings'] = ['invalid']
        bad_templates.append(value_template)
        for value_template in bad_templates:
            with self.subTest(template=value_template), patch('apps.appointments.hms.request_json', return_value=value_template):
                with self.assertRaises(VideoServiceUnavailable):
                    validate_template('template-test', configured_roles())
        with patch('apps.appointments.hms.request_json', return_value=template()):
            validate_template('template-test', configured_roles())

    def test_invalid_provider_room_shape_fails_explicitly(self):
        reservation = SimpleNamespace(room_name='consultation-test', template_id='template-test')
        with self.assertRaises(VideoServiceUnavailable):
            checked_room({
                'id': 'room-test', 'name': None, 'template_id': 'template-test',
                'enabled': True, 'recording_info': {'enabled': False},
            }, reservation)
