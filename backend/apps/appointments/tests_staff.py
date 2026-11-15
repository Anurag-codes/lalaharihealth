import tempfile
from datetime import time, timedelta
from unittest.mock import patch

from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.consultations.models import Consultation, ConsultationDocument
from apps.doctors.models import DoctorProfile, Speciality
from apps.payments.models import Payment
from .availability import local_datetime
from .models import Appointment, AppointmentCall, AppointmentSlot, AppointmentVideoRoom

PASSWORD = 'staff-test-password-1'


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class StaffConsoleTestBase(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username='ops', password=PASSWORD, role='admin', is_staff=True, first_name='Priya', last_name='Verma',
        )
        self.patient = User.objects.create_user(
            username='patient', role='patient', first_name='Rahul', last_name='Sharma', phone_number='+919876543210',
        )
        self.day = timezone.localdate() + timedelta(days=2)
        self.doctor = self.make_doctor('ananya', 'Ananya')
        self.doctor2 = self.make_doctor('vikram', 'Vikram')
        self.client.force_authenticate(self.staff)

    def make_doctor(self, username, first_name, speciality=None, verified=True):
        doctor = User.objects.create_user(
            username=username, role='doctor', first_name=first_name, last_name='Rao', phone_number=f'+91980000{len(username):04d}',
        )
        DoctorProfile.objects.create(
            user=doctor, specialization='General Physician', qualification='MBBS', registration_number=f'REG-{username}',
            speciality=speciality, verification_status='verified' if verified else 'pending', experience_years=5,
        )
        return doctor

    def at(self, hour, minute=0, day=None):
        return local_datetime(day or self.day, time(hour, minute))

    def booking(self, starts_at=None, status='finding_doctor', paid=True, doctor=None, speciality=None, **consultation):
        values = {
            'patient': self.patient, 'doctor': doctor, 'speciality': speciality, 'mode': 'video', 'status': 'requested',
            'patient_name': 'Priya Sharma', 'patient_age': 33, 'patient_gender': 'female',
            'patient_phone': '+919876543211', 'patient_relation': 'spouse', 'fee_charged': 200, 'history_completed': True,
            'scheduled_at': starts_at or self.at(10), **consultation,
        }
        record = Consultation.objects.create(**values)
        appointment = Appointment.objects.create(
            consultation=record, patient=self.patient, doctor=doctor, slot_time=starts_at or self.at(10), status=status,
        )
        if paid:
            Payment.objects.create(user=self.patient, consultation=record, amount=200, status=Payment.Status.SUCCESS)
        return appointment


class StaffAuthTests(StaffConsoleTestBase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def login(self, username='ops', password=PASSWORD):
        return self.client.post('/api/v1/auth/staff/login/', {'username': username, 'password': password}, format='json')

    def test_only_active_staff_receive_tokens_and_logout_revokes_refresh(self):
        response = self.login()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response.data['user']['full_name'], 'Priya Verma')
        self.assertNotIn('password', str(response.data))
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')
        self.assertEqual(self.client.get('/api/v1/staff/me/').data['username'], 'ops')
        self.assertEqual(self.client.post('/api/v1/auth/staff/logout/', {'refresh': response.data['refresh']}, format='json').status_code, 204)
        refreshed = APIClient().post('/api/v1/auth/token/refresh/', {'refresh': response.data['refresh']}, format='json')
        self.assertEqual(refreshed.status_code, 401)

        self.doctor.set_password(PASSWORD)
        self.doctor.save()
        inactive = User.objects.create_user(username='former', password=PASSWORD, is_staff=True, is_active=False)
        for username, password in (('ops', 'wrong-password'), ('ananya', PASSWORD), (inactive.username, PASSWORD), ('nobody', PASSWORD)):
            failed = self.login(username, password)
            self.assertEqual(failed.status_code, 401, username)
            self.assertEqual(failed.data['detail'], 'Invalid username or password.')
            self.assertNotIn('access', failed.data)

    @override_settings(STAFF_LOGIN_USER_HOURLY_LIMIT=2)
    def test_login_attempts_are_rate_limited_per_username(self):
        self.assertEqual(self.login(password='wrong').status_code, 401)
        self.assertEqual(self.login(username=' OPS ', password='wrong').status_code, 401)
        self.assertEqual(self.login().status_code, 429)

    def test_staff_endpoints_reject_patients_doctors_and_anonymous(self):
        appointment = self.booking()
        paths = [
            '/api/v1/staff/me/', '/api/v1/staff/summary/', '/api/v1/staff/appointments/',
            f'/api/v1/staff/appointments/{appointment.pk}/', f'/api/v1/staff/appointments/{appointment.pk}/doctors/',
            '/api/v1/staff/doctors/', f'/api/v1/staff/doctors/{self.doctor.pk}/schedule/?date={self.day.isoformat()}',
        ]
        for user, expected in ((None, 401), (self.patient, 403), (self.doctor, 403)):
            self.client.force_authenticate(user)
            for path in paths:
                self.assertEqual(self.client.get(path).status_code, expected, (user, path))
            patch_response = self.client.patch(
                f'/api/v1/staff/appointments/{appointment.pk}/patient/', {'patient_name': 'X'}, format='json',
            )
            self.assertEqual(patch_response.status_code, expected)
        appointment.consultation.refresh_from_db()
        self.assertEqual(appointment.consultation.patient_name, 'Priya Sharma')


class StaffAppointmentTests(StaffConsoleTestBase):
    def ids(self, response):
        self.assertEqual(response.status_code, 200, response.data)
        return [row['id'] for row in response.data['results']]

    def test_queues_filters_search_and_summary(self):
        waiting = self.booking(self.at(11))
        overdue = self.booking(timezone.now() - timedelta(hours=1))
        unpaid = self.booking(self.at(12), status='awaiting_payment', paid=False)
        done = self.booking(self.at(9), status='completed', doctor=self.doctor)
        confirmed = self.booking(self.at(13), status='confirmed', doctor=self.doctor2)
        url = '/api/v1/staff/appointments/'
        self.assertEqual(self.ids(self.client.get(url, {'queue': 'needs_doctor'})), [overdue.pk, waiting.pk])
        self.assertEqual(self.ids(self.client.get(url, {'queue': 'overdue'})), [overdue.pk])
        self.assertEqual(self.ids(self.client.get(url, {'queue': 'awaiting_payment'})), [unpaid.pk])
        self.assertEqual(self.ids(self.client.get(url, {'queue': 'completion_pending'})), [done.pk])
        self.assertEqual(self.ids(self.client.get(url, {'queue': 'upcoming'})), [confirmed.pk])
        self.assertEqual(self.ids(self.client.get(url, {'doctor_id': self.doctor2.pk})), [confirmed.pk])
        self.assertEqual(self.ids(self.client.get(url, {'q': f'APT-{waiting.pk:05d}'})), [waiting.pk])
        self.assertEqual(len(self.ids(self.client.get(url, {'q': '98765 43210'}))), 5)
        self.assertEqual(self.ids(self.client.get(url, {'q': 'vikram'})), [confirmed.pk])
        dated = self.client.get(url, {'date_from': self.day.isoformat(), 'date_to': self.day.isoformat(), 'ordering': 'slot_time'})
        self.assertEqual(self.ids(dated), [done.pk, waiting.pk, unpaid.pk, confirmed.pk])
        self.assertEqual(self.client.get(url, {'queue': 'bogus'}).status_code, 400)
        self.assertEqual(self.client.get(url, {'date_from': '2026-02-02', 'date_to': '2026-02-01'}).status_code, 400)

        rows = {row['id']: row for row in self.client.get(url).data['results']}
        self.assertTrue(rows[overdue.pk]['is_overdue'])
        self.assertEqual((rows[waiting.pk]['can_assign'], rows[waiting.pk]['lock_reason']), (True, None))
        self.assertEqual(rows[unpaid.pk]['lock_reason'], 'Only paid or approved free appointments awaiting a doctor, or confirmed appointments, can be assigned.')
        self.assertTrue(rows[done.pk]['needs_completion_confirmation'])
        self.assertFalse(rows[done.pk]['can_edit_patient'])
        self.assertEqual(rows[confirmed.pk]['doctor']['name'], 'Dr. Vikram Rao')
        self.assertEqual(rows[waiting.pk]['category']['name'], 'General Physician')
        self.assertEqual(rows[waiting.pk]['amount_display'], '\u20b9200')
        self.assertEqual(rows[waiting.pk]['booker'], {'id': self.patient.pk, 'name': 'Rahul Sharma', 'phone': '+919876543210'})

        summary = self.client.get('/api/v1/staff/summary/').data
        self.assertEqual(
            (summary['needs_doctor'], summary['overdue'], summary['awaiting_payment'], summary['completion_pending'], summary['upcoming_confirmed']),
            (2, 1, 1, 1, 1),
        )

    def test_detail_reports_locks_documents_and_calls(self):
        confirmed = self.booking(status='confirmed', doctor=self.doctor)
        detail = self.client.get(f'/api/v1/staff/appointments/{confirmed.pk}/')
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertTrue(detail.data['can_assign'])
        self.assertEqual(detail.data['payment']['status'], 'success')
        self.assertEqual((detail.data['booker']['name'], detail.data['booker']['email']), ('Rahul Sharma', ''))
        AppointmentCall.objects.create(appointment=confirmed, provider='100ms', status='unknown')
        self.assertTrue(self.client.get(f'/api/v1/staff/appointments/{confirmed.pk}/').data['can_assign'])
        AppointmentVideoRoom.objects.create(appointment=confirmed, template_id='template', room_id='room-1')
        locked = self.client.get(f'/api/v1/staff/appointments/{confirmed.pk}/').data
        self.assertFalse(locked['can_assign'])
        self.assertTrue(locked['video_room_provisioned'])
        self.assertIn('video join credentials', locked['lock_reason'])
        self.assertEqual(len(locked['calls']), 1)
        unpaid = self.booking(paid=False)
        self.assertEqual(self.client.get(f'/api/v1/staff/appointments/{unpaid.pk}/').data['lock_reason'], 'Confirmed payment is required.')
        self.assertEqual(self.client.get('/api/v1/staff/appointments/999999/').status_code, 404)

    def test_document_download(self):
        storage = FileSystemStorage(location=tempfile.mkdtemp())
        with patch.object(ConsultationDocument._meta.get_field('file'), 'storage', storage):
            appointment = self.booking()
            document = ConsultationDocument.objects.create(
                consultation=appointment.consultation, original_name='report.pdf',
                file=SimpleUploadedFile('report.pdf', b'%PDF-1.4 staff'),
            )
            path = self.client.get(f'/api/v1/staff/appointments/{appointment.pk}/').data['documents'][0]['download_path']
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4 staff')
            self.assertIn('attachment', response['Content-Disposition'])
            response.close()
            other = self.booking()
            self.assertEqual(self.client.get(f'/api/v1/staff/appointments/{other.pk}/documents/{document.pk}/download/').status_code, 404)

    def test_patient_snapshot_edit_rules(self):
        appointment = self.booking()
        url = f'/api/v1/staff/appointments/{appointment.pk}/patient/'
        response = self.client.patch(url, {'patient_name': '  Priya S Sharma ', 'patient_age': 34}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((response.data['patient_name'], response.data['patient_age']), ('Priya S Sharma', 34))
        for payload in ({'patient_phone': '+919999999999'}, {}, {'patient_age': 121}, {'patient_gender': 'x'}, {'patient_name': ' '}):
            self.assertEqual(self.client.patch(url, payload, format='json').status_code, 400, payload)
        Appointment.objects.filter(pk=appointment.pk).update(status='cancelled')
        self.assertEqual(self.client.patch(url, {'patient_age': 40}, format='json').status_code, 400)
        appointment.consultation.refresh_from_db()
        self.assertEqual((appointment.consultation.patient_age, appointment.consultation.patient_phone), (34, '+919876543211'))


class StaffDoctorTests(StaffConsoleTestBase):
    def test_doctor_choices_show_availability_conflicts_and_category(self):
        skin = Speciality.objects.create(name='Staff Test Skin', slug='staff-test-skin', fee=400)
        self.make_doctor('meera', 'Meera', speciality=skin)
        self.make_doctor('pending', 'Pending', verified=False)
        busy = self.booking(self.at(10), status='confirmed', doctor=self.doctor2)
        AppointmentSlot.objects.create(doctor=self.doctor, starts_at=self.at(10))
        appointment = self.booking(self.at(10))
        response = self.client.get(f'/api/v1/staff/appointments/{appointment.pk}/doctors/')
        self.assertEqual(response.status_code, 200, response.data)
        rows = {row['id']: row for row in response.data['results']}
        self.assertEqual(set(rows), {self.doctor.pk, self.doctor2.pk})
        self.assertEqual([row['id'] for row in response.data['results']], [self.doctor.pk, self.doctor2.pk])
        self.assertTrue(rows[self.doctor.pk]['is_available'] and rows[self.doctor.pk]['has_open_slot'])
        self.assertFalse(rows[self.doctor2.pk]['is_available'])
        self.assertEqual(rows[self.doctor2.pk]['conflict']['appointment_id'], busy.pk)
        self.assertEqual(rows[self.doctor2.pk]['appointments_that_day'], 1)

        later = self.client.get(f'/api/v1/staff/appointments/{appointment.pk}/doctors/', {'starts_at': self.at(11).isoformat()})
        self.assertTrue(all(row['is_available'] and not row['has_open_slot'] for row in later.data['results']))
        for bad in (self.at(10, 7).isoformat(), (timezone.now() - timedelta(hours=1)).isoformat(), 'tomorrow'):
            self.assertEqual(self.client.get(
                f'/api/v1/staff/appointments/{appointment.pk}/doctors/', {'starts_at': bad},
            ).status_code, 400, bad)
        skin_booking = self.booking(speciality=skin)
        names = [row['name'] for row in self.client.get(f'/api/v1/staff/appointments/{skin_booking.pk}/doctors/').data['results']]
        self.assertEqual(names, ['Dr. Meera Rao'])

    def test_doctor_list_and_day_schedule(self):
        skin = Speciality.objects.create(name='Staff Test Skin', slug='staff-test-skin', fee=400)
        self.make_doctor('meera', 'Meera', speciality=skin)
        self.make_doctor('pending', 'Pending', verified=False)
        listing = self.client.get('/api/v1/staff/doctors/')
        self.assertEqual([row['name'] for row in listing.data], ['Dr. Ananya Rao', 'Dr. Meera Rao', 'Dr. Vikram Rao'])
        self.assertEqual([row['name'] for row in self.client.get('/api/v1/staff/doctors/', {'speciality': skin.pk}).data], ['Dr. Meera Rao'])
        self.assertEqual(len(self.client.get('/api/v1/staff/doctors/', {'speciality': 'general'}).data), 2)
        self.assertEqual([row['name'] for row in self.client.get('/api/v1/staff/doctors/', {'q': 'vik'}).data], ['Dr. Vikram Rao'])

        slot = AppointmentSlot.objects.create(doctor=self.doctor, starts_at=self.at(0, 15))
        appointment = self.booking(self.at(23, 45), status='confirmed', doctor=self.doctor)
        self.booking(self.at(23, 45), status='cancelled', doctor=self.doctor)
        response = self.client.get(f'/api/v1/staff/doctors/{self.doctor.pk}/schedule/', {'date': self.day.isoformat()})
        self.assertEqual(response.status_code, 200, response.data)
        times = response.data['times']
        self.assertEqual(len(times), 96)
        self.assertEqual((times[0]['time_display'], times[-1]['time_display']), ('12:00 AM', '11:45 PM'))
        self.assertEqual((times[1]['slot_open'], times[1]['slot_id']), (True, slot.pk))
        self.assertEqual(times[-1]['appointment']['id'], appointment.pk)
        self.assertFalse(any(row['is_past'] for row in times))
        self.assertEqual(self.client.get(f'/api/v1/staff/doctors/{self.doctor.pk}/schedule/').status_code, 400)
        self.assertEqual(self.client.get(f'/api/v1/staff/doctors/{self.patient.pk}/schedule/', {'date': self.day.isoformat()}).status_code, 404)

    def test_staff_jwt_drives_existing_assign_and_completion_endpoints(self):
        token = APIClient().post('/api/v1/auth/staff/login/', {'username': 'ops', 'password': PASSWORD}, format='json').data['access']
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        appointment = self.booking(self.at(10))
        assigned = client.post(f'/api/v1/appointments/{appointment.pk}/assign-doctor/', {
            'doctor_id': self.doctor.pk, 'starts_at': self.at(0, 30).isoformat(),
        }, format='json')
        self.assertEqual(assigned.status_code, 200, assigned.data)
        detail = client.get(f'/api/v1/staff/appointments/{appointment.pk}/').data
        self.assertEqual((detail['status'], detail['doctor']['id'], detail['schedule_time']), ('confirmed', self.doctor.pk, '12:30 AM'))
        Appointment.objects.filter(pk=appointment.pk).update(status='completed', completed_at=timezone.now())
        self.assertEqual(client.post(f'/api/v1/appointments/{appointment.pk}/confirm-completion/', {}, format='json').status_code, 200)
        detail = client.get(f'/api/v1/staff/appointments/{appointment.pk}/').data
        self.assertFalse(detail['needs_completion_confirmation'])
        self.assertEqual(detail['timeline']['completion_confirmed_by'], 'Priya Verma')
