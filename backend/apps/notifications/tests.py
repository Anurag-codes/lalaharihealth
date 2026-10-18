from datetime import time, timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.appointments.availability import local_datetime
from apps.appointments.models import Appointment, AppointmentSlot
from apps.consultations.models import Consultation
from apps.doctors.models import DoctorProfile, Speciality
from apps.patients.models import PatientProfile
from apps.payments.gateway import record_capture
from apps.payments.models import Payment
from .models import Announcement, DeviceToken, Notification
from .service import deliver_push, send_announcement

User = get_user_model()


class HomeTestBase(APITestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username='patient', role='patient', first_name='Rahul', last_name='Sharma', phone_number='+919876543210',
        )
        self.staff = User.objects.create_user(username='staff', is_staff=True)
        self.day = timezone.localdate() + timedelta(days=2)
        self.derma = Speciality.objects.create(
            name='Dermatology (test)', slug='dermatology-test', short_name='Derma', consultation_title='Skin Consultation', fee=400,
        )
        self.doctor = self.make_doctor('doc1')

    def make_doctor(self, username, speciality=None, fee=200):
        doctor = User.objects.create_user(username=username, role='doctor', first_name='Ananya', last_name='Sharma')
        DoctorProfile.objects.create(
            user=doctor, specialization='Dermatologist' if speciality else 'General Physician', systems_practiced='allopathy',
            qualification='MBBS', registration_number=f'REG-{username}', consultation_fee=fee,
            verification_status='verified', speciality=speciality,
        )
        return doctor

    def slot(self, doctor, hour, minute=0, day=None):
        return AppointmentSlot.objects.create(doctor=doctor, starts_at=local_datetime(day or self.day, time(hour, minute)))

    def draft(self, speciality=None, history=True):
        self.client.force_authenticate(self.patient)
        details = {'patient_name': 'Rahul Sharma', 'patient_age': 25, 'patient_gender': 'male', 'mode': 'video'}
        if speciality is not None:
            details['speciality'] = speciality.pk
        response = self.client.post('/api/v1/consultations/', details, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        consultation_id = response.data['id']
        if history:
            response = self.client.put(
                f'/api/v1/consultations/{consultation_id}/history/',
                {'duration_value': 2, 'duration_unit': 'days', 'ongoing_medication': False}, format='json',
            )
            self.assertEqual(response.status_code, 200, response.data)
        return consultation_id

    def submit(self, consultation_id, slot):
        self.client.force_authenticate(self.patient)
        return self.client.post(
            '/api/v1/appointments/', {'consultation_id': consultation_id, 'slot_id': slot.pk, 'information_confirmed': True},
            format='json',
        )

    def book_and_pay(self, speciality=None, doctor=None, hour=10):
        response = self.submit(self.draft(speciality), self.slot(doctor or self.doctor, hour))
        self.assertEqual(response.status_code, 201, response.data)
        appointment = Appointment.objects.get(pk=response.data['id'])
        fee = appointment.consultation.fee_charged
        payment = Payment.objects.create(
            user=self.patient, consultation=appointment.consultation, amount=fee, gateway_order_id=f'order_{appointment.pk}',
        )
        record_capture(payment.pk, {
            'id': f'pay_{appointment.pk}', 'order_id': payment.gateway_order_id, 'amount': fee * 100,
            'currency': 'INR', 'status': 'captured', 'method': 'upi',
        })
        appointment.refresh_from_db()
        return appointment

    def assign(self, appointment, doctor):
        self.client.force_authenticate(self.staff)
        return self.client.post(f'/api/v1/appointments/{appointment.pk}/assign-doctor/', {'doctor_id': doctor.pk}, format='json')


class NotificationEventTests(HomeTestBase):
    def test_booking_lifecycle_creates_notifications(self):
        appointment = self.book_and_pay()
        self.assertEqual(appointment.status, 'finding_doctor')
        self.assertIsNotNone(appointment.paid_at)
        paid = Notification.objects.get(user=self.patient, kind='payment_success')
        self.assertEqual(paid.title, 'Payment successful')
        self.assertIn(f'APT-{appointment.pk:05d}', paid.body)
        self.assertIn('\u20b9200', paid.body)

        self.assertEqual(self.assign(appointment, self.doctor).status_code, 200)
        appointment.refresh_from_db()
        self.assertIsNotNone(appointment.doctor_assigned_at)
        confirmed = Notification.objects.get(kind='doctor_assigned')
        self.assertIn('Dr. Ananya Sharma', confirmed.body)
        self.assertIn('10:00 AM', confirmed.body)

        self.client.force_authenticate(self.doctor)
        response = self.client.put(
            f'/api/v1/doctors/me/consultations/{appointment.consultation_id}/record/',
            {'diagnosis': 'Viral fever', 'prescriptions': [], 'mark_completed': True}, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        appointment.refresh_from_db()
        self.assertIsNotNone(appointment.completed_at)
        self.assertEqual(Notification.objects.get(kind='consultation_completed').title, 'Prescription ready')
        # Saving the record again does not notify twice.
        self.client.put(
            f'/api/v1/doctors/me/consultations/{appointment.consultation_id}/record/',
            {'diagnosis': 'Viral fever', 'prescriptions': [], 'mark_completed': True}, format='json',
        )
        self.assertEqual(Notification.objects.filter(kind='consultation_completed').count(), 1)

    def test_hindi_users_get_hindi_text(self):
        PatientProfile.objects.update_or_create(user=self.patient, defaults={'preferred_language': 'hi'})
        self.book_and_pay()
        self.assertEqual(Notification.objects.get(kind='payment_success').title, '\u092d\u0941\u0917\u0924\u093e\u0928 \u0938\u092b\u0932')

    def test_admin_release_notifies_cancellation(self):
        from django.contrib.admin.sites import site
        from django.test import RequestFactory

        response = self.submit(self.draft(), self.slot(self.doctor, 11))
        appointment = Appointment.objects.get(pk=response.data['id'])
        model_admin = site._registry[Appointment]
        request = RequestFactory().post('/')
        request.user = self.staff
        with patch.object(model_admin, 'message_user'):
            model_admin.release_unstarted_reservations(request, Appointment.objects.filter(pk=appointment.pk))
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'cancelled')
        self.assertIsNotNone(appointment.cancelled_at)
        self.assertEqual(Notification.objects.get(kind='appointment_cancelled').appointment_id, appointment.pk)

    def test_reminder_command_sends_once(self):
        appointment = self.book_and_pay()
        self.assign(appointment, self.doctor)
        Appointment.objects.filter(pk=appointment.pk).update(slot_time=timezone.now() + timedelta(minutes=20))
        out = StringIO()
        call_command('send_appointment_reminders', stdout=out)
        call_command('send_appointment_reminders', stdout=out)
        self.assertIn('Sent 1 appointment reminder(s).', out.getvalue())
        self.assertEqual(Notification.objects.filter(kind='appointment_reminder').count(), 1)


class NotificationApiTests(HomeTestBase):
    def setUp(self):
        super().setUp()
        self.first = Notification.objects.create(user=self.patient, kind='announcement', title='Hello', body='One')
        self.second = Notification.objects.create(user=self.patient, kind='announcement', title='Hi', body='Two')
        other = User.objects.create_user(username='other', role='patient')
        self.foreign = Notification.objects.create(user=other, kind='announcement', title='X', body='Y')
        self.client.force_authenticate(self.patient)

    def test_requires_patient_token(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/v1/notifications/').status_code, 401)

    def test_list_read_and_counts(self):
        self.assertEqual(self.client.get('/api/v1/notifications/').data['count'], 2)
        self.assertEqual(self.client.get('/api/v1/notifications/unread-count/').data, {'unread_count': 2})
        response = self.client.post(f'/api/v1/notifications/{self.first.pk}/read/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_read'])
        unread = self.client.get('/api/v1/notifications/', {'unread': 'true'}).data
        self.assertEqual([row['id'] for row in unread['results']], [self.second.pk])
        self.assertEqual(self.client.post(f'/api/v1/notifications/{self.foreign.pk}/read/').status_code, 404)
        self.assertEqual(self.client.post('/api/v1/notifications/read-all/').data, {'marked_read': 1})
        self.assertEqual(self.client.get('/api/v1/notifications/unread-count/').data, {'unread_count': 0})

    def test_device_tokens(self):
        response = self.client.post('/api/v1/notifications/devices/', {'token': 'fcm-abc', 'platform': 'android'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        other = User.objects.get(username='other')
        self.client.force_authenticate(other)
        self.client.post('/api/v1/notifications/devices/', {'token': 'fcm-abc', 'platform': 'android'}, format='json')
        self.assertEqual(DeviceToken.objects.get(token='fcm-abc').user, other)
        self.assertEqual(self.client.post('/api/v1/notifications/devices/remove/', {'token': 'fcm-abc'}, format='json').status_code, 204)
        self.assertFalse(DeviceToken.objects.filter(token='fcm-abc').exists())

    def test_announcement_is_sent_once_in_users_language(self):
        PatientProfile.objects.update_or_create(user=self.patient, defaults={'preferred_language': 'hi'})
        announcement = Announcement.objects.create(
            title='Health camp', body='Free check-up on Sunday', title_hi='\u0938\u094d\u0935\u093e\u0938\u094d\u0925\u094d\u092f \u0936\u093f\u0935\u093f\u0930',
            audience='patients',
        )
        patients = User.objects.filter(is_active=True, role='patient').count()
        self.assertEqual(send_announcement(announcement), patients)
        self.assertEqual(send_announcement(announcement), 0)
        mine = Notification.objects.get(user=self.patient, announcement=announcement)
        self.assertEqual(mine.title, announcement.title_hi)
        self.assertEqual(mine.body, 'Free check-up on Sunday')
        self.assertFalse(Notification.objects.filter(user=self.doctor, announcement=announcement).exists())

    def test_deliver_push_deactivates_stale_tokens(self):
        from firebase_admin import messaging

        DeviceToken.objects.create(user=self.patient, token='good', platform='android')
        DeviceToken.objects.create(user=self.patient, token='stale', platform='ios')

        def send_each(message, app=None):
            return SimpleNamespace(responses=[
                SimpleNamespace(exception=messaging.UnregisteredError('gone') if token == 'stale' else None)
                for token in message.tokens
            ])

        with patch('apps.accounts.firebase.firebase_app', return_value=object()), \
                patch.object(messaging, 'send_each_for_multicast', side_effect=send_each) as send, \
                patch('apps.notifications.service.connection.close'):
            deliver_push([self.first.pk])
        message = send.call_args.args[0]
        self.assertEqual(sorted(message.tokens), ['good', 'stale'])
        self.assertEqual(message.data['notification_id'], str(self.first.pk))
        self.assertFalse(DeviceToken.objects.get(token='stale').is_active)
        self.assertTrue(DeviceToken.objects.get(token='good').is_active)


class SpecialityBookingTests(HomeTestBase):
    def test_public_list_shows_active_specialities_only(self):
        Speciality.objects.create(name='Hidden', slug='hidden', fee=900, is_active=False)
        self.client.force_authenticate(None)
        names = [row['name'] for row in self.client.get('/api/v1/doctors/specialities/').data]
        self.assertIn('Dermatology (test)', names)
        self.assertNotIn('Hidden', names)

    def test_specialist_booking_uses_speciality_fee_slots_and_doctors(self):
        dermatologist = self.make_doctor('derm', speciality=self.derma, fee=400)
        general_slot = self.slot(self.doctor, 10)
        derm_slot = self.slot(dermatologist, 11)
        self.client.force_authenticate(self.patient)
        day = self.day.isoformat()
        general = self.client.get('/api/v1/appointments/slots/', {'date': day}).data
        special = self.client.get('/api/v1/appointments/slots/', {'date': day, 'speciality_id': self.derma.pk}).data
        self.assertEqual([row['id'] for row in general], [general_slot.pk])
        self.assertEqual([row['id'] for row in special], [derm_slot.pk])
        counts = {
            row['date']: row['available_slot_count']
            for row in self.client.get('/api/v1/appointments/slot-dates/', {'speciality_id': self.derma.pk}).data
        }
        self.assertEqual(counts[day], 1)
        general_counts = {row['date']: row['available_slot_count'] for row in self.client.get('/api/v1/appointments/slot-dates/').data}
        self.assertEqual(general_counts[day], 1)

        consultation_id = self.draft(self.derma)
        self.assertEqual(self.submit(consultation_id, general_slot).status_code, 400)
        preview = self.client.get(f'/api/v1/consultations/{consultation_id}/preview/', {'slot_id': derm_slot.pk}).data
        self.assertEqual((preview['fee'], preview['consultation_title']), (400, 'Skin Consultation'))
        response = self.submit(consultation_id, derm_slot)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual((response.data['amount'], response.data['consultation_title']), (400, 'Skin Consultation'))
        self.assertEqual(response.data['speciality'], 'Dermatology (test)')

    def test_assign_requires_matching_speciality(self):
        appointment = self.book_and_pay()
        dermatologist = self.make_doctor('derm', speciality=self.derma, fee=200)
        self.slot(dermatologist, 10)
        self.assertEqual(self.assign(appointment, dermatologist).status_code, 404)
        self.assertEqual(self.assign(appointment, self.doctor).status_code, 200)


class HomeAndCasesTests(HomeTestBase):
    def test_home_screen(self):
        Notification.objects.create(user=self.patient, kind='announcement', title='Hi', body='There')
        confirmed = self.book_and_pay(hour=10)
        self.assign(confirmed, self.doctor)
        dermatologist = self.make_doctor('derm', speciality=self.derma, fee=400)
        self.book_and_pay(speciality=self.derma, doctor=dermatologist, hour=12)
        self.draft()

        self.client.force_authenticate(self.patient)
        data = self.client.get('/api/v1/patients/home/').data
        self.assertEqual(data['greeting_name'], 'Rahul Sharma')
        self.assertEqual(data['general_care'], {
            'title': 'General Consultation', 'country_code': 'IN', 'fee': 200, 'currency': 'INR',
            'fee_display': '\u20b9200', 'match_within_minutes': 30,
        })
        # 1 announcement + 2 payment_success + 1 doctor_assigned
        self.assertEqual(data['unread_notification_count'], 4)
        self.assertIn('Dermatology (test)', [row['name'] for row in data['specialities']])
        first, second = data['upcoming_appointments']
        local = timezone.localtime(confirmed.slot_time)
        self.assertEqual((first['day'], first['month'], first['time']), (local.strftime('%d'), local.strftime('%b').upper(), '10:00 AM'))
        self.assertEqual((first['title'], first['doctor_name'], first['status_label']), ('General Consultation', 'Dr. Ananya Sharma', 'Confirmed'))
        self.assertEqual((second['title'], second['doctor_name'], second['status']), ('Skin Consultation', None, 'finding_doctor'))
        self.assertEqual(first['mode_label'], 'Online')
        self.assertEqual(data['active_case_count'], 3)

    def test_cases_tracker_and_filters(self):
        paid = self.book_and_pay()
        draft_id = self.draft(history=False)
        unpaid = self.submit(self.draft(), self.slot(self.doctor, 13)).data
        done = self.book_and_pay(hour=14)
        Appointment.objects.filter(pk=done.pk).update(status='completed', completed_at=timezone.now())

        self.client.force_authenticate(self.patient)
        cases = {row['consultation_id']: row for row in self.client.get('/api/v1/patients/cases/').data['results']}
        self.assertEqual(len(cases), 4)
        self.assertEqual((cases[draft_id]['stage'], cases[draft_id]['next_action']), ('draft', 'complete_history'))
        self.assertIsNone(cases[draft_id]['schedule'])
        self.assertEqual(cases[unpaid['consultation']]['next_action'], 'pay')
        tracked = cases[paid.consultation_id]
        self.assertEqual((tracked['stage'], tracked['next_action']), ('finding_doctor', 'wait_for_doctor'))
        self.assertEqual([step['done'] for step in tracked['tracker']], [True, True, False, False])
        self.assertEqual(tracked['schedule']['time'], '10:00 AM')
        self.assertEqual(cases[done.consultation_id]['next_action'], 'view_record')

        active = self.client.get('/api/v1/patients/cases/', {'status': 'active'}).data
        closed = self.client.get('/api/v1/patients/cases/', {'status': 'closed'}).data
        self.assertEqual((active['count'], closed['count']), (3, 1))
        self.assertEqual(self.client.get('/api/v1/patients/cases/', {'status': 'x'}).status_code, 400)
        detail = self.client.get(f'/api/v1/patients/cases/{paid.consultation_id}/').data
        self.assertEqual(detail['appointment_number'], f'APT-{paid.pk:05d}')

        other = User.objects.create_user(username='other', role='patient')
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(f'/api/v1/patients/cases/{paid.consultation_id}/').status_code, 404)
        self.assertEqual(Consultation.objects.filter(patient=other).count(), 0)
