import io
import tempfile
import time as clock
from datetime import date, timedelta
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.models import User, VerifiedIdentity
from apps.appointments.models import Appointment
from apps.notifications.models import Notification
from apps.notifications.tests import HomeTestBase
from .models import DoctorApplication, DoctorApplicationDocument, DoctorDocument, DoctorProfile

PDF = b'%PDF-1.4\n%test\n'
PHONE = '+919812345678'


def png_bytes():
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), 'white').save(buffer, format='PNG')
    return buffer.getvalue()


class DoctorAppBase(HomeTestBase):
    def setUp(self):
        super().setUp()
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        private = tempfile.TemporaryDirectory()
        self.addCleanup(private.cleanup)
        settings_patch = override_settings(MEDIA_ROOT=media.name, FIREBASE_PROJECT_ID='test-project')
        settings_patch.enable()
        self.addCleanup(settings_patch.disable)
        storage_patch = patch.object(
            DoctorDocument._meta.get_field('file'), 'storage', FileSystemStorage(location=private.name),
        )
        storage_patch.start()
        self.addCleanup(storage_patch.stop)
        self.app = APIClient()
        self.token_counter = 0

    def claims(self, phone=PHONE, uid='firebase-doctor-1'):
        return {
            'uid': uid, 'phone_number': phone, 'auth_time': int(clock.time()), 'exp': int(clock.time()) + 3600,
            'firebase': {'sign_in_provider': 'phone'},
        }

    def sign_in(self, phone=PHONE, uid='firebase-doctor-1', client=None):
        self.token_counter += 1
        with patch('apps.accounts.doctor_views.verify_phone_token', return_value=self.claims(phone, uid)):
            return (client or self.app).post(
                '/api/v1/auth/doctor/phone/firebase/', {'id_token': f'doctor-token-{self.token_counter}'}, format='json',
            )

    def signed_in(self, phone=PHONE):
        response = self.sign_in(phone)
        self.assertEqual(response.status_code, 200, response.data)
        self.app.credentials(HTTP_AUTHORIZATION=f'Bearer {response.data["access"]}')
        return response

    def verify(self, user):
        DoctorProfile.objects.filter(user=user).update(verification_status='verified')


class DoctorAuthTests(DoctorAppBase):
    def test_new_number_creates_pending_doctor_account(self):
        response = self.sign_in()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertTrue(response.data['is_new_user'])
        user = User.objects.get(pk=response.data['doctor']['id'])
        self.assertEqual(user.role, 'doctor')
        self.assertTrue(user.username.startswith('doctor_'), user.username)
        self.assertEqual(user.phone_number, PHONE)
        self.assertEqual(response.data['doctor']['verification_status'], 'pending')
        self.assertEqual(response.data['doctor']['onboarding']['next_step'], 'profile')
        identity = VerifiedIdentity.objects.get(user=user)
        self.assertEqual((identity.role, identity.kind, identity.value), ('doctor', 'phone', PHONE))

        again = self.sign_in()
        self.assertEqual(again.status_code, 200, again.data)
        self.assertFalse(again.data['is_new_user'])
        self.assertEqual(again.data['doctor']['id'], user.pk)

    def test_same_phone_keeps_patient_and_doctor_accounts_separate(self):
        with patch('apps.accounts.views.verify_phone_token', return_value=self.claims(uid='firebase-shared')):
            patient = self.app.post('/api/v1/auth/patient/phone/firebase/', {'id_token': 'patient-token'}, format='json')
        self.assertEqual(patient.status_code, 200, patient.data)
        doctor = self.sign_in(uid='firebase-shared')
        self.assertEqual(doctor.status_code, 200, doctor.data)
        patient_user = User.objects.get(role='patient', phone_number=PHONE)
        doctor_user = User.objects.get(role='doctor', phone_number=PHONE)
        self.assertNotEqual(patient_user.pk, doctor_user.pk)
        self.assertEqual(doctor.data['doctor']['id'], doctor_user.pk)

        self.app.credentials(HTTP_AUTHORIZATION=f'Bearer {doctor.data["access"]}')
        self.assertEqual(self.app.get('/api/v1/patients/profile/').status_code, 403)
        self.app.credentials(HTTP_AUTHORIZATION=f'Bearer {patient.data["access"]}')
        self.assertEqual(self.app.get('/api/v1/doctors/me/').status_code, 403)

        refresh = self.app.post('/api/v1/auth/patient/token/refresh/', {'refresh': doctor.data['refresh']}, format='json')
        self.assertEqual(refresh.status_code, 401)
        refresh = self.app.post('/api/v1/auth/doctor/token/refresh/', {'refresh': patient.data['refresh']}, format='json')
        self.assertEqual(refresh.status_code, 401)
        refresh = self.app.post('/api/v1/auth/doctor/token/refresh/', {'refresh': doctor.data['refresh']}, format='json')
        self.assertEqual(refresh.status_code, 200, refresh.data)

    def test_reused_firebase_token_is_rejected(self):
        with patch('apps.accounts.doctor_views.verify_phone_token', return_value=self.claims()):
            first = self.app.post('/api/v1/auth/doctor/phone/firebase/', {'id_token': 'same'}, format='json')
            second = self.app.post('/api/v1/auth/doctor/phone/firebase/', {'id_token': 'same'}, format='json')
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(second.status_code, 401)

    def test_staff_created_doctor_account_is_claimed(self):
        existing = User.objects.create_user(username='dr_existing', role='doctor', phone_number=PHONE, first_name='Meera')
        response = self.sign_in()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data['is_new_user'])
        self.assertEqual(response.data['doctor']['id'], existing.pk)
        self.assertEqual(User.objects.filter(role='doctor', phone_number=PHONE).count(), 1)

    def test_logout_revokes_refresh_token(self):
        response = self.signed_in()
        logout = self.app.post('/api/v1/auth/doctor/logout/', {'refresh': response.data['refresh']}, format='json')
        self.assertEqual(logout.status_code, 204)
        refresh = self.app.post('/api/v1/auth/doctor/token/refresh/', {'refresh': response.data['refresh']}, format='json')
        self.assertEqual(refresh.status_code, 401)


class ApplicationImportTests(DoctorAppBase):
    def application(self, **fields):
        application = DoctorApplication.objects.create(**{
            'full_name': 'Dr. Kavya Iyer', 'phone_number': '98123 45678', 'email': 'kavya@example.com',
            'qualification': 'MBBS, MD', 'experience_years': 9, 'consultation_category': 'specialist',
            'specialization': 'derma', 'city': 'Chennai', 'treatment_systems': ['allopathy', 'unknown'],
            'status': 'approved', **fields,
        })
        DoctorApplicationDocument.objects.create(application=application, file=ContentFile(PDF, name='degree.pdf'))
        return application

    def test_matching_form_entry_is_copied_and_stays_pending(self):
        DoctorApplication.objects.create(full_name='Other', phone_number='9000000000')
        application = self.application()
        response = self.sign_in()
        self.assertEqual(response.status_code, 200, response.data)
        doctor = response.data['doctor']
        self.assertEqual((doctor['first_name'], doctor['last_name']), ('Kavya', 'Iyer'))
        self.assertEqual(doctor['email'], 'kavya@example.com')
        self.assertEqual(doctor['qualification'], 'MBBS, MD')
        self.assertEqual(doctor['experience_years'], 9)
        self.assertEqual(doctor['city'], 'Chennai')
        self.assertEqual(doctor['speciality'], {'id': self.derma.pk, 'name': self.derma.name})
        self.assertEqual(doctor['verification_status'], 'pending')
        self.assertEqual(len(doctor['documents']), 1)
        self.assertEqual(doctor['documents'][0]['document_type'], 'other')
        profile = DoctorProfile.objects.get(user_id=doctor['id'])
        self.assertEqual(profile.application, application)
        self.assertEqual(profile.systems_practiced, 'allopathy')
        self.assertEqual(profile.user.city, 'Chennai')

    def test_number_typed_with_country_code_matches(self):
        self.application(phone_number='+91 98123-45678', consultation_category='general', specialization='')
        doctor = self.sign_in().data['doctor']
        self.assertIsNone(doctor['speciality'])
        self.assertEqual(doctor['specialization'], 'General Physician')
        self.assertEqual(doctor['first_name'], 'Kavya')

    def test_phone_matching_needs_the_full_number(self):
        from .onboarding import same_phone

        self.assertTrue(same_phone('98123 45678', '+919812345678'))
        self.assertTrue(same_phone('098123-45678', '+919812345678'))
        self.assertTrue(same_phone('+1 720 234 5678', '+17202345678'))
        self.assertFalse(same_phone('7202345678', '+17202345678'))
        self.assertFalse(same_phone('7202345678', '+917202345678', 'US'))
        self.assertFalse(same_phone('2345678', '+917202345678'))
        self.assertFalse(same_phone('', '+917202345678'))

    def test_foreign_number_with_same_digits_is_not_imported(self):
        self.application()
        doctor = self.sign_in(phone='+19812345678').data['doctor']
        self.assertEqual(doctor['first_name'], '')
        self.assertEqual(doctor['documents'], [])

    def test_different_number_is_not_imported(self):
        self.application(phone_number='9812345679')
        doctor = self.sign_in().data['doctor']
        self.assertEqual(doctor['first_name'], '')
        self.assertEqual(doctor['documents'], [])


class DoctorProfileTests(DoctorAppBase):
    def details(self, **overrides):
        return {
            'full_name': 'Dr. Ananya Rao', 'age': 34, 'gender': 'female', 'registration_number': 'DMC/R/777',
            'qualification': 'MBBS', 'speciality_id': None, **overrides,
        }

    def upload(self, document_type='medical_registration', name='registration.pdf', content=PDF):
        return self.app.post(
            '/api/v1/doctors/me/documents/',
            {'document_type': document_type, 'file': SimpleUploadedFile(name, content)}, format='multipart',
        )

    def availability(self, days):
        return self.app.put('/api/v1/doctors/me/availability/', {'days': days}, format='json')

    def test_requires_doctor_token(self):
        self.assertEqual(self.app.get('/api/v1/doctors/me/').status_code, 401)
        self.app.force_authenticate(self.patient)
        self.assertEqual(self.app.get('/api/v1/doctors/me/').status_code, 403)

    def test_onboarding_steps(self):
        self.signed_in()
        response = self.app.patch('/api/v1/doctors/me/', self.details(), format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['full_name'], 'Ananya Rao')
        self.assertEqual(response.data['registration_number'], 'DMC/R/777')
        self.assertTrue(response.data['onboarding']['profile_completed'])
        self.assertEqual(response.data['onboarding']['next_step'], 'profile')

        upload = self.upload()
        self.assertEqual(upload.status_code, 201, upload.data)
        me = self.app.get('/api/v1/doctors/me/').data
        self.assertEqual(me['onboarding']['next_step'], 'availability')

        week = self.availability([{'weekday': 0, 'is_open': True, 'windows': [
            {'start_time': '21:00', 'end_time': '23:00'}, {'start_time': '07:00', 'end_time': '10:00'},
            {'start_time': '15:00', 'end_time': '16:00'},
        ]}])
        self.assertEqual(week.status_code, 200, week.data)
        monday = week.data['days'][0]
        self.assertEqual([window['start_time'] for window in monday['windows']], ['07:00', '15:00', '21:00'])
        self.assertEqual(monday['total_hours'], 6.0)
        self.assertEqual(monday['windows'][0]['display'], '07:00 AM - 10:00 AM')
        self.assertFalse(week.data['days'][1]['is_open'])
        me = self.app.get('/api/v1/doctors/me/').data
        self.assertTrue(me['onboarding']['is_complete'])
        self.assertEqual(me['onboarding']['next_step'], 'done')

    def test_profile_validation(self):
        self.signed_in()
        DoctorProfile.objects.create(user=User.objects.create_user(username='other', role='doctor'), registration_number='TAKEN-1')
        self.assertEqual(self.app.patch('/api/v1/doctors/me/', {'registration_number': 'taken-1'}, format='json').status_code, 400)
        self.assertEqual(self.app.patch('/api/v1/doctors/me/', {'is_verified': True}, format='json').status_code, 400)
        self.assertEqual(self.app.patch('/api/v1/doctors/me/', {'speciality_id': 99999}, format='json').status_code, 400)
        self.assertEqual(self.app.patch('/api/v1/doctors/me/', {'age': 12}, format='json').status_code, 400)
        response = self.app.patch('/api/v1/doctors/me/', {'speciality_id': self.derma.pk}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['specialization'], self.derma.name)
        response = self.app.patch('/api/v1/doctors/me/', {'registration_number': ''}, format='json')
        self.assertIsNone(response.data['registration_number'])

    def test_verified_details_are_locked(self):
        response = self.signed_in()
        self.app.patch('/api/v1/doctors/me/', self.details(), format='json')
        self.verify(response.data['doctor']['id'])
        locked = self.app.patch('/api/v1/doctors/me/', {'qualification': 'MD'}, format='json')
        self.assertEqual(locked.status_code, 400)
        self.assertIn('qualification', locked.data)
        same = self.app.patch('/api/v1/doctors/me/', {'qualification': 'MBBS', 'age': 35}, format='json')
        self.assertEqual(same.status_code, 200, same.data)
        self.assertEqual(same.data['age'], 35)

    def test_documents(self):
        response = self.signed_in()
        first = self.upload()
        second = self.upload(name='new-registration.pdf')
        self.assertEqual(second.status_code, 201, second.data)
        documents = self.app.get('/api/v1/doctors/me/documents/').data
        self.assertEqual([document['id'] for document in documents], [second.data['id']])
        self.assertFalse(DoctorDocument.objects.filter(pk=first.data['id']).exists())
        self.assertEqual(self.upload(name='fake.pdf', content=b'not a pdf').status_code, 400)

        download = self.app.get(f'/api/v1/doctors/me/documents/{second.data["id"]}/download/')
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b''.join(download.streaming_content), PDF)
        self.assertIn('new-registration.pdf', download['Content-Disposition'])

        other = APIClient()
        other_login = self.sign_in(phone='+919800000001', uid='firebase-doctor-2', client=other)
        self.assertEqual(other_login.status_code, 200, other_login.data)
        other.credentials(HTTP_AUTHORIZATION=f'Bearer {other_login.data["access"]}')
        self.assertEqual(other.get(f'/api/v1/doctors/me/documents/{second.data["id"]}/download/').status_code, 404)

        self.verify(response.data['doctor']['id'])
        self.assertEqual(self.app.delete(f'/api/v1/doctors/me/documents/{second.data["id"]}/').status_code, 400)
        extra = self.upload(document_type='other', name='id.png', content=png_bytes())
        self.assertEqual(extra.status_code, 201, extra.data)
        self.assertEqual(self.app.delete(f'/api/v1/doctors/me/documents/{extra.data["id"]}/').status_code, 204)

    def test_photo(self):
        self.signed_in()
        upload = SimpleUploadedFile('me.png', png_bytes(), content_type='image/png')
        response = self.app.put('/api/v1/doctors/me/photo/', {'photo': upload}, format='multipart')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn('/media/doctors/', response.data['photo_url'])
        self.assertEqual(self.app.delete('/api/v1/doctors/me/photo/').status_code, 204)
        self.assertIsNone(self.app.get('/api/v1/doctors/me/').data['photo_url'])

    def test_availability_rules(self):
        self.signed_in()
        window = lambda start, end: {'start_time': start, 'end_time': end}  # noqa: E731
        cases = [
            [{'weekday': 0, 'is_open': True, 'windows': [window('09:00', '14:00')]}],
            [{'weekday': 0, 'is_open': True, 'windows': [window('09:00', '13:00'), window('12:00', '16:00')]}],
            [{'weekday': 0, 'is_open': True, 'windows': [
                window('06:00', '08:00'), window('09:00', '11:00'), window('12:00', '14:00'), window('15:00', '17:00'),
            ]}],
            [{'weekday': 0, 'is_open': True, 'windows': [window('09:10', '15:10')]}],
            [{'weekday': 0, 'is_open': False, 'windows': []}],
            [{'weekday': 0, 'is_open': True, 'windows': [window('09:00', '15:00')]},
             {'weekday': 0, 'is_open': True, 'windows': [window('09:00', '15:00')]}],
        ]
        for days in cases:
            with self.subTest(days=days):
                self.assertEqual(self.availability(days).status_code, 400)
        ok = self.availability([
            {'weekday': 2, 'is_open': True, 'windows': [window('09:00', '15:00')]},
            {'weekday': 3, 'is_open': False, 'windows': [window('01:00', '02:00')]},
        ])
        self.assertEqual(ok.status_code, 200, ok.data)
        self.assertEqual(sum(len(day['windows']) for day in ok.data['days']), 1)
        self.assertEqual(self.app.get('/api/v1/doctors/me/availability/').data, ok.data)

    def test_qualification_suggestions_are_public(self):
        response = APIClient().get('/api/v1/doctors/qualifications/?search=md')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data)
        self.assertTrue(all('md' in item['name'].lower() for item in response.data))


class DoctorAppointmentTests(DoctorAppBase):
    def setUp(self):
        super().setUp()
        self.doctor_client = APIClient()
        self.doctor_client.force_authenticate(self.doctor)

    def assigned(self, hour=10, starts_at=None):
        appointment = self.book_and_pay(hour=hour)
        self.assertEqual(self.assign(appointment, self.doctor).status_code, 200)
        if starts_at is not None:
            Appointment.objects.filter(pk=appointment.pk).update(slot_time=starts_at)
        appointment.refresh_from_db()
        return appointment

    def complete(self, appointment):
        return self.doctor_client.patch(
            f'/api/v1/doctors/me/appointments/{appointment.pk}/', {'status': 'completed'}, format='json',
        )

    def test_pending_doctor_cannot_see_appointments(self):
        DoctorProfile.objects.filter(user=self.doctor).update(verification_status='pending')
        self.assertEqual(self.doctor_client.get('/api/v1/doctors/me/schedule/').status_code, 403)
        self.assertEqual(self.doctor_client.get('/api/v1/doctors/me/earnings/').status_code, 403)
        self.assertEqual(self.doctor_client.get('/api/v1/doctors/me/').status_code, 200)

    def test_assignment_notifies_doctor_and_shows_in_schedule(self):
        appointment = self.assigned()
        notification = Notification.objects.get(user=self.doctor, kind='appointment_assigned')
        self.assertEqual(notification.title, 'New appointment booked')
        self.assertIn('Rahul Sharma booked a General Consultation', notification.body)

        schedule = self.doctor_client.get(f'/api/v1/doctors/me/schedule/?date={self.day.isoformat()}')
        self.assertEqual(schedule.status_code, 200, schedule.data)
        self.assertEqual([item['id'] for item in schedule.data], [appointment.pk])
        self.assertEqual(schedule.data[0]['time_display'], '10:00 AM - 10:15 AM')
        self.assertFalse(schedule.data[0]['can_join'])
        other_day = self.doctor_client.get(f'/api/v1/doctors/me/schedule/?date={(self.day + timedelta(days=1)).isoformat()}')
        self.assertEqual(other_day.data, [])

        detail = self.doctor_client.get(f'/api/v1/doctors/me/appointments/{appointment.pk}/')
        self.assertEqual(detail.status_code, 200, detail.data)
        self.assertEqual(detail.data['patient']['name'], 'Rahul Sharma')
        self.assertEqual(detail.data['patient']['age'], 25)
        self.assertEqual(detail.data['patient']['phone_number'], '+919876543210')
        self.assertEqual(detail.data['fee'], 200)

        stranger = APIClient()
        stranger.force_authenticate(self.make_doctor('doc2'))
        self.assertEqual(stranger.get(f'/api/v1/doctors/me/appointments/{appointment.pk}/').status_code, 404)

    def test_completion_window_and_idempotence(self):
        appointment = self.assigned()
        early = self.complete(appointment)
        self.assertEqual(early.status_code, 400)

        Appointment.objects.filter(pk=appointment.pk).update(slot_time=timezone.now() + timedelta(minutes=3))
        detail = self.doctor_client.get(f'/api/v1/doctors/me/appointments/{appointment.pk}/')
        self.assertTrue(detail.data['can_join'])
        done = self.complete(appointment)
        self.assertEqual(done.status_code, 200, done.data)
        self.assertEqual(done.data['status'], 'completed')
        self.assertFalse(done.data['can_join'])
        self.assertFalse(done.data['completion_confirmed'])
        appointment.refresh_from_db()
        self.assertEqual(appointment.consultation.status, 'completed')
        self.assertEqual(Notification.objects.filter(user=self.patient, kind='consultation_completed').count(), 1)

        again = self.complete(appointment)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(Notification.objects.filter(user=self.patient, kind='consultation_completed').count(), 1)
        self.assertEqual(
            self.doctor_client.patch(f'/api/v1/doctors/me/appointments/{appointment.pk}/', {'status': 'cancelled'}, format='json').status_code,
            400,
        )

    def test_staff_confirm_completion(self):
        appointment = self.assigned()
        url = f'/api/v1/appointments/{appointment.pk}/confirm-completion/'
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post(url).status_code, 400)
        Appointment.objects.filter(pk=appointment.pk).update(slot_time=timezone.now())
        self.assertEqual(self.complete(appointment).status_code, 200)
        self.client.force_authenticate(self.patient)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post(url).status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.completion_confirmed_by, self.staff)
        confirmed_at = appointment.completion_confirmed_at
        self.assertEqual(self.client.post(url).status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.completion_confirmed_at, confirmed_at)
        detail = self.doctor_client.get(f'/api/v1/doctors/me/appointments/{appointment.pk}/')
        self.assertTrue(detail.data['completion_confirmed'])

    def test_doctor_can_take_another_patient_at_same_time_after_completion(self):
        first = self.assigned()
        second = self.book_and_pay()
        clash = self.assign(second, self.doctor)
        self.assertEqual(clash.status_code, 400)
        self.assertIn('already has an appointment', str(clash.data))

        Appointment.objects.filter(pk=first.pk).update(slot_time=timezone.now())
        self.assertEqual(self.complete(first).status_code, 200)
        Appointment.objects.filter(pk=first.pk).update(slot_time=second.slot_time)
        self.assertEqual(self.assign(second, self.doctor).status_code, 200)

    def test_call_details(self):
        appointment = self.assigned()
        url = f'/api/v1/doctors/me/appointments/{appointment.pk}/calls/'
        created = self.doctor_client.post(url, {
            'mode': 'video', 'provider': 'agora', 'external_call_id': 'room-1', 'started_at': '2026-10-18T10:31:00+05:30',
        }, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.assertIsNone(created.data['duration_minutes'])
        updated = self.doctor_client.patch(f'{url}{created.data["id"]}/', {'ended_at': '2026-10-18T10:43:30+05:30'}, format='json')
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data['duration_seconds'], 750)
        self.assertEqual(updated.data['duration_minutes'], 13)
        backwards = self.doctor_client.patch(f'{url}{created.data["id"]}/', {'ended_at': '2026-10-18T10:00:00+05:30'}, format='json')
        self.assertEqual(backwards.status_code, 400)
        self.assertEqual(self.doctor_client.post(url, {'unknown': 1}, format='json').status_code, 400)
        detail = self.doctor_client.get(f'/api/v1/doctors/me/appointments/{appointment.pk}/')
        self.assertEqual(len(detail.data['calls']), 1)

        stranger = APIClient()
        stranger.force_authenticate(self.make_doctor('doc2'))
        self.assertEqual(stranger.post(url, {}, format='json').status_code, 404)

    def test_earnings_by_period(self):
        today = timezone.localdate()
        morning, evening = self.assigned(hour=10), self.assigned(hour=11)
        for appointment, hour in ((morning, 9), (evening, 21)):
            Appointment.objects.filter(pk=appointment.pk).update(slot_time=timezone.now())
            self.assertEqual(self.complete(appointment).status_code, 200)
            Appointment.objects.filter(pk=appointment.pk).update(slot_time=self.at(hour, day=today))
        evening.consultation.__class__.objects.filter(pk=evening.consultation_id).update(mode='audio')
        self.assigned(hour=12, starts_at=self.at(10, day=today))  # confirmed, not completed: not counted

        daily = self.doctor_client.get('/api/v1/doctors/me/earnings/')
        self.assertEqual(daily.status_code, 200, daily.data)
        self.assertEqual(daily.data['period'], 'daily')
        self.assertEqual(daily.data['total_earned'], 400)
        self.assertEqual(daily.data['total_earned_display'], '\u20b9400')
        self.assertEqual(daily.data['consultations_count'], 2)
        self.assertEqual(daily.data['average_per_consultation'], 200)
        self.assertEqual(len(daily.data['chart']), 12)
        self.assertEqual(daily.data['chart'][4], {'label': '8 AM', 'amount': 200, 'count': 1})
        self.assertEqual(daily.data['chart'][10]['amount'], 200)
        self.assertEqual([entry['mode'] for entry in daily.data['by_mode']], ['video', 'audio', 'chat'])
        self.assertEqual(daily.data['by_mode'][0]['share_percent'], 50.0)
        self.assertIsNone(daily.data['next_date'])
        self.assertTrue(daily.data['is_current'])

        monthly = self.doctor_client.get(f'/api/v1/doctors/me/earnings/?period=monthly&date={today.isoformat()}').data
        self.assertEqual(monthly['total_earned'], 400)
        self.assertEqual(monthly['chart'][today.day - 1]['count'], 2)
        self.assertEqual(monthly['start_date'], today.replace(day=1).isoformat())

        fy = self.doctor_client.get('/api/v1/doctors/me/earnings/?period=financial_year').data
        start_year = today.year if today.month >= 4 else today.year - 1
        self.assertEqual(fy['label'], f'FY {start_year}-{str(start_year + 1)[-2:]}')
        self.assertEqual(fy['start_date'], date(start_year, 4, 1).isoformat())
        self.assertEqual(len(fy['chart']), 12)
        self.assertEqual(fy['chart'][0]['label'], 'Apr')
        self.assertEqual(fy['total_earned'], 400)

        last_year = self.doctor_client.get(f'/api/v1/doctors/me/earnings/?period=daily&date={(today - timedelta(days=400)).isoformat()}').data
        self.assertEqual(last_year['total_earned'], 0)
        self.assertIsNotNone(last_year['next_date'])
        self.assertEqual(self.doctor_client.get('/api/v1/doctors/me/earnings/?period=weekly').status_code, 400)


class DoctorAdminTests(DoctorAppBase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser(username='admin', password='unused-test-password', email='admin@example.com')
        self.client.force_login(self.admin)
        self.profile = DoctorProfile.objects.create(
            user=User.objects.create_user(username='pending_doc', role='doctor'), specialization='General Physician',
        )

    def change(self, status):
        data = {
            'user': self.profile.user_id, 'specialization': 'General Physician', 'systems_practiced': '',
            'qualification': '', 'registration_number': '', 'experience_years': 0, 'bio': '',
            'consultation_fee': 0, 'currency': 'INR', 'languages_spoken': '', 'city': '',
            'verification_status': status, 'average_rating': '0', 'is_active': 'on', 'age': '', 'gender': '',
        }
        for prefix in ('documents', 'availability_windows'):
            data.update({f'{prefix}-TOTAL_FORMS': '0', f'{prefix}-INITIAL_FORMS': '0'})
        return self.client.post(f'/admin/doctors/doctorprofile/{self.profile.pk}/change/', data)

    def test_verifying_notifies_doctor_once(self):
        response = self.change('verified')
        self.assertEqual(response.status_code, 302, getattr(response, 'context', None) and response.context['adminform'].form.errors)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.verification_status, 'verified')
        self.assertIsNone(self.profile.registration_number)
        notification = Notification.objects.get(user=self.profile.user, kind='verification_update')
        self.assertEqual(notification.title, 'Profile verified')
        self.assertEqual(self.change('verified').status_code, 302)
        self.assertEqual(Notification.objects.filter(user=self.profile.user, kind='verification_update').count(), 1)

    def test_staff_can_download_private_document(self):
        document = DoctorDocument(doctor=self.profile, document_type='medical_registration', original_name='reg.pdf')
        document.file.save('reg.pdf', ContentFile(PDF))
        response = self.client.get(f'/admin/doctors/doctorprofile/document/{document.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), PDF)
        self.client.logout()
        self.assertEqual(self.client.get(f'/admin/doctors/doctorprofile/document/{document.pk}/').status_code, 302)
        page = APIClient()
        page.force_login(self.admin)
        self.assertContains(page.get(f'/admin/doctors/doctorprofile/{self.profile.pk}/change/'), 'Download')

    def test_confirm_completion_action(self):
        appointment = self.book_and_pay()
        self.assign(appointment, self.doctor)
        Appointment.objects.filter(pk=appointment.pk).update(status='completed')
        self.client.force_login(self.admin)
        response = self.client.post('/admin/appointments/appointment/', {
            'action': 'confirm_completion', '_selected_action': [appointment.pk],
        })
        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.completion_confirmed_by, self.admin)
        self.assertIsNotNone(appointment.completion_confirmed_at)


class DocumentStorageMigrationTests(DoctorAppBase):
    def test_existing_public_documents_move_to_private_storage(self):
        import importlib

        from django.apps import apps as django_apps
        from django.conf import settings

        migration = importlib.import_module('apps.doctors.migrations.0011_move_doctor_documents_to_private_storage')
        profile = DoctorProfile.objects.create(user=User.objects.create_user(username='old_doc', role='doctor'))
        public = FileSystemStorage(location=settings.MEDIA_ROOT)
        private = DoctorDocument._meta.get_field('file').storage
        name = public.save('doctors/documents/old-registration.pdf', ContentFile(PDF))
        DoctorDocument.objects.create(doctor=profile, document_type='medical_registration', file=name)

        with patch('apps.core.storage.private_document_storage', return_value=private):
            migration.move_documents_to_private_storage(django_apps, None)
            migration.move_documents_to_private_storage(django_apps, None)
        self.assertFalse(public.exists(name))
        with private.open(name, 'rb') as handle:
            self.assertEqual(handle.read(), PDF)
