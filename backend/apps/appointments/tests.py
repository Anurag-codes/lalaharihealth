from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.consultations.models import Consultation
from apps.doctors.models import DoctorProfile
from apps.payments.models import Payment
from apps.notifications.models import Notification
from apps.notifications.tests import HomeTestBase
from apps.treatments.models import Condition
from .availability import local_datetime
from .models import Appointment, AppointmentCall, AppointmentSlot, AppointmentVideoRoom

User = get_user_model()


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class BookingFlowTests(APITestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username='patient', role='patient', first_name='Rahul', last_name='Sharma', phone_number='+919876543210',
        )
        self.day = timezone.localdate() + timedelta(days=2)
        self.doctor = self.make_doctor('doc1')
        self.doctor2 = self.make_doctor('doc2')

    def make_doctor(self, username, verified=True):
        doctor = User.objects.create_user(username=username, role='doctor', first_name='Ananya', last_name=username)
        DoctorProfile.objects.create(
            user=doctor, specialization='General Physician', systems_practiced='allopathy', qualification='MBBS',
            registration_number=f'REG-{username}', consultation_fee=200,
            verification_status='verified' if verified else 'pending',
        )
        return doctor

    def at(self, hour, minute=0, day=None):
        return local_datetime(day or self.day, time(hour, minute))

    def slot(self, doctor, hour, minute=0):
        return AppointmentSlot.objects.create(doctor=doctor, starts_at=self.at(hour, minute))

    def draft(self, user=None, history=None):
        self.client.force_authenticate(user or self.patient)
        details = {'patient_name': 'Rahul Sharma', 'patient_age': 25, 'patient_gender': 'male', 'patient_phone': '9876543210', 'mode': 'video'}
        consultation_id = self.client.post('/api/v1/consultations/', details, format='json').data['id']
        history = history or {'duration_value': 5, 'duration_unit': 'days', 'ongoing_medication': False}
        response = self.client.put(f'/api/v1/consultations/{consultation_id}/history/', history, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        return consultation_id

    def submit(self, consultation_id, starts_at, confirmed=True):
        return self.client.post(
            '/api/v1/appointments/',
            {'consultation_id': consultation_id, 'starts_at': starts_at.isoformat(), 'information_confirmed': confirmed}, format='json',
        )

    def pay(self, appointment_id):
        appointment = Appointment.objects.get(pk=appointment_id)
        appointment.save(update_fields=appointment.set_status(Appointment.Status.FINDING_DOCTOR))
        Payment.objects.create(
            user=appointment.patient, consultation=appointment.consultation, amount=appointment.consultation.fee_charged,
            status=Payment.Status.SUCCESS,
        )
        return appointment

    def assign(self, appointment_id, doctor):
        self.client.force_authenticate(User.objects.get_or_create(username='staff', defaults={'is_staff': True})[0])
        return self.client.post(f'/api/v1/appointments/{appointment_id}/assign-doctor/', {'doctor_id': doctor.pk}, format='json')

    def test_assignment_can_move_to_free_time_when_requested_time_is_busy(self):
        busy = self.pay(self.submit(self.draft(), self.at(10)).data['id'])
        self.assertEqual(self.assign(busy.pk, self.doctor).status_code, 200)
        replacement = self.slot(self.doctor, 0)
        appointment = self.pay(self.submit(self.draft(), self.at(10)).data['id'])
        fee = appointment.consultation.fee_charged
        self.client.force_authenticate(User.objects.get(username='staff'))
        response = self.client.post(f'/api/v1/appointments/{appointment.pk}/assign-doctor/', {
            'doctor_id': self.doctor.pk, 'starts_at': self.at(0).isoformat(),
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        appointment.refresh_from_db()
        appointment.consultation.refresh_from_db()
        self.assertEqual(appointment.slot_time, self.at(0))
        self.assertEqual(appointment.consultation.scheduled_at, self.at(0))
        self.assertEqual(appointment.slot_id, replacement.pk)
        self.assertEqual(appointment.status, 'confirmed')
        self.assertEqual(appointment.consultation.fee_charged, fee)
        self.assertEqual(response.data['schedule_time'], '12:00 AM')
        notification = Notification.objects.get(appointment=appointment, kind='doctor_assigned')
        self.assertIn('12:00 AM', notification.body)
        self.client.force_authenticate(self.doctor)
        schedule = self.client.get('/api/v1/doctors/me/schedule/', {'date': self.day.isoformat()})
        changed = next(item for item in schedule.data if item['id'] == appointment.pk)
        self.assertEqual(datetime.fromisoformat(changed['starts_at']), self.at(0))

    def test_replacement_assignment_rejects_busy_or_invalid_time_without_changes(self):
        busy = self.pay(self.submit(self.draft(), self.at(11)).data['id'])
        self.assertEqual(self.assign(busy.pk, self.doctor).status_code, 200)
        appointment = self.pay(self.submit(self.draft(), self.at(10)).data['id'])
        self.client.force_authenticate(User.objects.get(username='staff'))
        url = f'/api/v1/appointments/{appointment.pk}/assign-doctor/'
        for starts_at in (self.at(11), self.at(10, 7), timezone.now() - timedelta(hours=1), self.at(10, day=self.day + timedelta(days=31))):
            with self.subTest(starts_at=starts_at):
                response = self.client.post(url, {
                    'doctor_id': self.doctor.pk, 'starts_at': starts_at.isoformat(),
                }, format='json')
                self.assertEqual(response.status_code, 400, response.data)
                appointment.refresh_from_db()
                appointment.consultation.refresh_from_db()
                self.assertEqual(appointment.status, 'finding_doctor')
                self.assertEqual(appointment.slot_time, self.at(10))
                self.assertEqual(appointment.consultation.scheduled_at, self.at(10))
                self.assertIsNone(appointment.doctor_id)
        self.assertFalse(Notification.objects.filter(appointment=appointment, kind='doctor_assigned').exists())

    def test_confirmed_time_only_reassignment_and_idempotence(self):
        appointment = self.pay(self.submit(self.draft(), self.at(10)).data['id'])
        self.assertEqual(self.assign(appointment.pk, self.doctor).status_code, 200)
        appointment.refresh_from_db()
        assigned_at = appointment.doctor_assigned_at
        fee = appointment.consultation.fee_charged
        url = f'/api/v1/appointments/{appointment.pk}/assign-doctor/'
        slot = self.slot(self.doctor, 12)
        response = self.client.post(url, {'starts_at': self.at(12).isoformat()}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        appointment.refresh_from_db()
        appointment.consultation.refresh_from_db()
        self.assertEqual((appointment.doctor_id, appointment.slot_id, appointment.slot_time), (self.doctor.pk, slot.pk, self.at(12)))
        self.assertEqual((appointment.consultation.doctor_id, appointment.consultation.scheduled_at), (self.doctor.pk, self.at(12)))
        self.assertEqual(appointment.consultation.fee_charged, fee)
        self.assertEqual(appointment.doctor_assigned_at, assigned_at)
        Appointment.objects.filter(pk=appointment.pk).update(reminder_sent_at=timezone.now())
        other_slot = self.slot(self.doctor2, 12)
        response = self.client.post(url, {'doctor_id': self.doctor2.pk}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        appointment.refresh_from_db()
        appointment.consultation.refresh_from_db()
        self.assertEqual((appointment.doctor_id, appointment.slot_id), (self.doctor2.pk, other_slot.pk))
        self.assertEqual(appointment.consultation.doctor_id, self.doctor2.pk)
        self.assertIsNone(appointment.reminder_sent_at)
        count = Notification.objects.filter(appointment=appointment).count()
        response = self.client.post(url, {'doctor_id': self.doctor2.pk, 'starts_at': self.at(12).isoformat()}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        appointment.refresh_from_db()
        self.assertEqual(appointment.doctor_assigned_at, assigned_at)
        self.assertEqual(Notification.objects.filter(appointment=appointment).count(), count)

    def test_confirmed_edit_rejects_started_calls_status_and_video_credentials(self):
        appointment = self.pay(self.submit(self.draft(), self.at(10)).data['id'])
        self.assertEqual(self.assign(appointment.pk, self.doctor).status_code, 200)
        url = f'/api/v1/appointments/{appointment.pk}/assign-doctor/'
        payload = {'starts_at': self.at(12).isoformat()}
        for status in (Consultation.Status.ONGOING, Consultation.Status.COMPLETED, Consultation.Status.CANCELLED):
            Consultation.objects.filter(pk=appointment.consultation_id).update(status=status)
            self.assertEqual(self.client.post(url, payload, format='json').status_code, 400, status)
        Consultation.objects.filter(pk=appointment.consultation_id).update(status=Consultation.Status.REQUESTED)
        for fields in ({'started_at': timezone.now()}, {'status': 'in_progress'}, {'status': 'completed'}, {'duration_seconds': 1}):
            call = AppointmentCall.objects.create(appointment=appointment, **fields)
            self.assertEqual(self.client.post(url, payload, format='json').status_code, 400, fields)
            call.delete()
        room = AppointmentVideoRoom.objects.create(appointment=appointment, template_id='template', room_id='room')
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Issued video join credentials', str(response.data))
        self.assertEqual(self.client.post(url, {}, format='json').status_code, 200)
        room.room_id = None
        room.save(update_fields=['room_id'])
        self.assertEqual(self.client.post(url, payload, format='json').status_code, 200)

    def test_confirmed_edits_still_validate_doctor_time_and_conflicts(self):
        busy = self.pay(self.submit(self.draft(), self.at(11)).data['id'])
        self.assertEqual(self.assign(busy.pk, self.doctor2).status_code, 200)
        appointment = self.pay(self.submit(self.draft(), self.at(10)).data['id'])
        self.assertEqual(self.assign(appointment.pk, self.doctor).status_code, 200)
        url = f'/api/v1/appointments/{appointment.pk}/assign-doctor/'
        pending = self.make_doctor('pending', verified=False)
        for payload in (
            {'doctor_id': self.doctor2.pk, 'starts_at': self.at(11).isoformat()},
            {'starts_at': self.at(10, 7).isoformat()},
            {'starts_at': (timezone.now() - timedelta(hours=1)).isoformat()},
            {'starts_at': self.at(10, day=self.day + timedelta(days=31)).isoformat()},
            {'doctor_id': pending.pk},
        ):
            self.assertIn(self.client.post(url, payload, format='json').status_code, (400, 404), payload)
            appointment.refresh_from_db()
            self.assertEqual((appointment.doctor_id, appointment.slot_time), (self.doctor.pk, self.at(10)))
        unassigned = self.pay(self.submit(self.draft(), self.at(13)).data['id'])
        self.client.force_authenticate(User.objects.get(username='staff'))
        self.assertEqual(self.client.post(f'/api/v1/appointments/{unassigned.pk}/assign-doctor/', {}, format='json').status_code, 400)

    # Symptoms dropdowns

    def test_condition_tree_and_history_hierarchy(self):
        self.client.force_authenticate(self.patient)
        response = self.client.get('/api/v1/consultations/conditions/')
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), Condition.objects.filter(is_active=True).count())
        headache = next(item for item in response.data if item['name'] == 'Headache')
        self.assertEqual(headache['type_label'], 'Specific Headache Type')
        cluster = next(item for item in headache['types'] if item['name'] == 'Cluster Headache')
        chronic = next(item for item in cluster['variants'] if item['name'] == 'Chronic')
        migraine = next(item for item in headache['types'] if item['name'] == 'Migraine')

        base = {'condition': headache['id'], 'duration_value': 3, 'duration_unit': 'days', 'ongoing_medication': False}
        consultation_id = self.draft()
        url = f'/api/v1/consultations/{consultation_id}/history/'
        self.assertIn('condition_type', self.client.put(url, base, format='json').data)
        self.assertIn('condition_variant', self.client.put(url, {**base, 'condition_type': cluster['id']}, format='json').data)
        mismatched = {**base, 'condition_type': migraine['id'], 'condition_variant': chronic['id']}
        self.assertIn('condition_variant', self.client.put(url, mismatched, format='json').data)
        fever = Condition.objects.get(name='Fever').types.first()
        self.assertIn('condition_type', self.client.put(url, {**base, 'condition_type': fever.pk}, format='json').data)

        valid = {**base, 'condition_type': cluster['id'], 'condition_variant': chronic['id'], 'condition_details': 'Night pain'}
        response = self.client.put(url, valid, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['chief_complaint'], 'Headache - Cluster Headache - Chronic')
        no_types = Condition.objects.get(name='Joint Pain')
        response = self.client.put(url, {**base, 'condition': no_types.pk}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['chief_complaint'], 'Joint Pain')

    # Doctor app slots

    def test_doctor_opens_15_minute_slots_from_chosen_time(self):
        self.client.force_authenticate(self.doctor)
        response = self.client.post('/api/v1/doctors/me/slots/', {'date': self.day.isoformat(), 'start_time': '22:00'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['created_count'], 8)
        self.assertEqual(response.data['slots'][0]['time_display'], '10:00 PM')
        self.assertEqual(response.data['slots'][-1]['time_display'], '11:45 PM')
        again = self.client.post('/api/v1/doctors/me/slots/', {'date': self.day.isoformat(), 'start_time': '22:00'}, format='json')
        self.assertEqual(again.status_code, 400)
        window = {'date': self.day.isoformat(), 'start_time': '19:00', 'end_time': '20:00'}
        self.assertEqual(self.client.post('/api/v1/doctors/me/slots/', window, format='json').data['created_count'], 4)
        listing = self.client.get('/api/v1/doctors/me/slots/', {'date': self.day.isoformat()})
        self.assertEqual(len(listing.data), 12)
        self.assertFalse(any(item['is_booked'] for item in listing.data))

    def test_doctor_slot_validation(self):
        self.client.force_authenticate(self.doctor)
        url = '/api/v1/doctors/me/slots/'
        for payload in [
            {'date': self.day.isoformat(), 'start_time': '19:10'},
            {'date': self.day.isoformat(), 'start_time': '24:00'},
            {'date': self.day.isoformat(), 'start_time': '19:00', 'end_time': '18:00'},
            {'date': (timezone.localdate() - timedelta(days=1)).isoformat(), 'start_time': '19:00'},
            {'date': (timezone.localdate() + timedelta(days=40)).isoformat(), 'start_time': '19:00'},
        ]:
            self.assertEqual(self.client.post(url, payload, format='json').status_code, 400, payload)
        self.client.force_authenticate(self.make_doctor('pending', verified=False))
        self.assertEqual(self.client.post(url, {'date': self.day.isoformat(), 'start_time': '19:00'}, format='json').status_code, 403)
        self.client.force_authenticate(self.patient)
        self.assertEqual(self.client.get(url, {'date': self.day.isoformat()}).status_code, 403)

    def test_doctor_can_remove_only_free_own_slots(self):
        booked = self.slot(self.doctor, 10)
        free = self.slot(self.doctor, 10, 15)
        foreign = self.slot(self.doctor2, 10, 30)
        appointment_id = self.submit(self.draft(), self.at(10)).data['id']
        self.pay(appointment_id)
        self.assertEqual(self.assign(appointment_id, self.doctor).status_code, 200)
        self.client.force_authenticate(self.doctor)
        listing = self.client.get('/api/v1/doctors/me/slots/', {'date': self.day.isoformat()}).data
        self.assertEqual((listing[0]['is_booked'], listing[0]['appointment_id']), (True, appointment_id))
        self.assertEqual(self.client.delete(f'/api/v1/doctors/me/slots/{booked.pk}/').status_code, 400)
        self.assertEqual(self.client.delete(f'/api/v1/doctors/me/slots/{foreign.pk}/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/v1/doctors/me/slots/{free.pk}/').status_code, 204)
        self.assertFalse(AppointmentSlot.objects.filter(pk=free.pk).exists())

    def test_doctor_can_open_all_96_slots_and_an_early_morning_window(self):
        self.client.force_authenticate(self.doctor)
        response = self.client.post('/api/v1/doctors/me/slots/', {
            'date': self.day.isoformat(), 'start_time': '00:00',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['created_count'], 96)
        self.assertEqual(len(response.data['slots']), 96)
        self.assertEqual(datetime.fromisoformat(response.data['slots'][0]['starts_at']), self.at(0))
        self.assertEqual(datetime.fromisoformat(response.data['slots'][-1]['starts_at']), self.at(23, 45))
        self.client.force_authenticate(self.doctor2)
        bounded = self.client.post('/api/v1/doctors/me/slots/', {
            'date': self.day.isoformat(), 'start_time': '00:00', 'end_time': '01:00',
        }, format='json')
        self.assertEqual(bounded.status_code, 201, bounded.data)
        self.assertEqual(bounded.data['created_count'], 4)
        self.assertEqual(datetime.fromisoformat(bounded.data['slots'][-1]['starts_at']), self.at(0, 45))

    # Patient Schedule Appointment

    def test_patient_sees_every_15_minute_time_without_doctor_slots(self):
        self.assertFalse(AppointmentSlot.objects.exists())
        self.client.force_authenticate(self.patient)
        response = self.client.get('/api/v1/appointments/slots/', {'date': self.day.isoformat()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 96)
        self.assertEqual(set(response.data[0]), {'starts_at', 'time_display'})
        self.assertEqual((response.data[0]['time_display'], response.data[1]['time_display']), ('12:00 AM', '12:15 AM'))
        self.assertEqual(response.data[-1]['time_display'], '11:45 PM')
        starts = [datetime.fromisoformat(row['starts_at']) for row in response.data]
        self.assertEqual(len(set(starts)), 96)
        self.assertTrue(all(later - earlier == timedelta(minutes=15) for earlier, later in zip(starts, starts[1:])))

        today = self.client.get('/api/v1/appointments/slots/', {'date': timezone.localdate().isoformat()}).data
        self.assertTrue(all(datetime.fromisoformat(item['starts_at']) > timezone.now() for item in today))
        for day in [timezone.localdate() - timedelta(days=1), timezone.localdate() + timedelta(days=31)]:
            self.assertEqual(self.client.get('/api/v1/appointments/slots/', {'date': day.isoformat()}).data, [])
        self.assertEqual(self.client.get('/api/v1/appointments/slots/').status_code, 400)

        dates = self.client.get('/api/v1/appointments/slot-dates/', {'days': 7}).data
        self.assertEqual(len(dates), 7)
        self.assertEqual((dates[0]['day_label'], dates[0]['available_slot_count']), ('Today', len(today)))
        self.assertEqual([row['available_slot_count'] for row in dates[1:]], [96] * 6)

    def test_full_day_slots_still_skip_past_times_today(self):
        today = timezone.localdate()
        now = local_datetime(today, time(1, 7))
        with patch('apps.appointments.availability.timezone.now', return_value=now):
            self.client.force_authenticate(self.patient)
            response = self.client.get('/api/v1/appointments/slots/', {'date': today.isoformat()})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(len(response.data), 91)
            self.assertEqual(datetime.fromisoformat(response.data[0]['starts_at']), local_datetime(today, time(1, 15)))
            self.client.force_authenticate(self.doctor)
            created = self.client.post('/api/v1/doctors/me/slots/', {
                'date': today.isoformat(), 'start_time': '00:00', 'end_time': '02:00',
            }, format='json')
            self.assertEqual(created.status_code, 201, created.data)
            self.assertEqual(created.data['created_count'], 3)
            self.assertTrue(all(datetime.fromisoformat(row['starts_at']) > now for row in created.data['slots']))

    # Case Preview and Submit Case

    def test_case_preview_then_submit_requires_confirmation(self):
        starts_at = self.at(19)
        consultation_id = self.draft()
        response = self.client.get(f'/api/v1/consultations/{consultation_id}/preview/', {'starts_at': starts_at.isoformat()})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['ready_to_submit'])
        self.assertEqual(response.data['chief_complaint'], 'General Consultation')
        self.assertEqual(response.data['schedule']['time_display'], '07:00 PM')
        self.assertNotIn('slot_id', response.data['schedule'])
        self.assertEqual(response.data['patient']['relation_label'], 'You')
        self.assertEqual(response.data['duration_display'], '5 Days')
        self.assertEqual((response.data['fee'], response.data['document_count']), (200, 0))
        self.assertFalse(Appointment.objects.exists())

        self.assertEqual(self.submit(consultation_id, starts_at, confirmed=False).status_code, 400)
        response = self.submit(consultation_id, starts_at)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual((response.data['schedule_time'], response.data['amount']), ('07:00 PM', 200))
        self.assertEqual((response.data['slot'], response.data['doctor'], response.data['status']), (None, None, 'awaiting_payment'))
        self.assertEqual(response.data['appointment_number'], f'APT-{response.data["id"]:05d}')
        consultation = Consultation.objects.get(pk=consultation_id)
        self.assertIsNotNone(consultation.information_confirmed_at)
        self.assertEqual(consultation.scheduled_at, starts_at)
        preview = self.client.get(f'/api/v1/consultations/{consultation_id}/preview/').data
        self.assertFalse(preview['ready_to_submit'])
        self.assertEqual(preview['schedule']['time_display'], '07:00 PM')

    def test_preview_flags_missing_steps(self):
        self.client.force_authenticate(self.patient)
        details = {'patient_name': 'Rahul Sharma', 'patient_age': 25, 'patient_gender': 'male', 'patient_phone': '9876543210'}
        consultation_id = self.client.post('/api/v1/consultations/', details, format='json').data['id']
        response = self.client.get(f'/api/v1/consultations/{consultation_id}/preview/')
        self.assertEqual(response.data['missing_steps'], ['history', 'schedule'])
        self.assertFalse(response.data['ready_to_submit'])

    def test_preview_accepts_unencoded_offset_and_flags_unselectable_times(self):
        consultation_id = self.draft()
        url = f'/api/v1/consultations/{consultation_id}/preview/'
        unencoded = self.client.get(f'{url}?starts_at={self.day.isoformat()}T19:00:00+05:30')
        self.assertEqual(unencoded.status_code, 200, unencoded.data)
        self.assertEqual(unencoded.data['schedule']['time_display'], '07:00 PM')
        self.assertTrue(unencoded.data['ready_to_submit'])
        for starts_at in [self.at(10, 10), timezone.now() - timedelta(hours=1)]:
            response = self.client.get(url, {'starts_at': starts_at.isoformat()})
            self.assertFalse(response.data['schedule']['is_available'], starts_at)
            self.assertEqual(response.data['missing_steps'], ['schedule'])
        self.assertEqual(self.client.get(url, {'starts_at': 'tomorrow'}).status_code, 400)

    def test_submit_rejects_times_patients_cannot_pick(self):
        consultation_id = self.draft()
        far = timezone.localdate() + timedelta(days=31)
        for starts_at in [
            self.at(10, 10), self.at(10, 0).replace(second=30),
            local_datetime(timezone.localdate() - timedelta(days=1), time(10)), local_datetime(far, time(10)),
        ]:
            response = self.submit(consultation_id, starts_at)
            self.assertEqual(response.status_code, 400, starts_at)
            self.assertIn('starts_at', response.data)
        self.assertEqual(self.submit(consultation_id, self.at(23, 45)).status_code, 201)
        self.assertFalse(Appointment.objects.filter(slot__isnull=False).exists())

    def test_patient_can_preview_book_and_assign_midnight_and_early_morning(self):
        for hour, minute in ((0, 0), (7, 45)):
            with self.subTest(hour=hour, minute=minute):
                starts_at = self.at(hour, minute)
                consultation_id = self.draft()
                preview = self.client.get(f'/api/v1/consultations/{consultation_id}/preview/', {
                    'starts_at': starts_at.isoformat(),
                })
                self.assertEqual(preview.status_code, 200, preview.data)
                self.assertTrue(preview.data['ready_to_submit'])
                submitted = self.submit(consultation_id, starts_at)
                self.assertEqual(submitted.status_code, 201, submitted.data)
                appointment = self.pay(submitted.data['id'])
                assigned = self.assign(appointment.pk, self.doctor)
                self.assertEqual(assigned.status_code, 200, assigned.data)
                appointment.consultation.refresh_from_db()
                self.assertEqual(appointment.consultation.scheduled_at, starts_at)

    def test_same_time_is_open_to_every_patient_and_repeat_is_idempotent(self):
        first = self.submit(self.draft(), self.at(10))
        self.assertEqual(first.status_code, 201, first.data)
        repeated = self.submit(first.data['consultation'], self.at(10))
        self.assertEqual((repeated.status_code, repeated.data['id']), (200, first.data['id']))
        self.assertEqual(self.submit(first.data['consultation'], self.at(11)).status_code, 400)
        other = User.objects.create_user(username='other', role='patient')
        self.assertEqual(self.submit(self.draft(user=other), self.at(10)).status_code, 201)
        self.assertEqual(Appointment.objects.filter(slot_time=self.at(10)).count(), 2)

    # Staff matching after payment

    def test_assign_any_verified_doctor_and_link_their_slot(self):
        appointment_id = self.submit(self.draft(), self.at(10)).data['id']
        self.assertEqual(self.assign(appointment_id, self.doctor).status_code, 400)  # not paid yet
        self.pay(appointment_id)
        url = f'/api/v1/appointments/{appointment_id}/assign-doctor/'
        self.assertEqual(self.client.post(url, {'doctor_id': self.make_doctor('pending', verified=False).pk}, format='json').status_code, 404)
        expensive = self.make_doctor('doc3')
        DoctorProfile.objects.filter(user=expensive).update(consultation_fee=900)
        target = self.slot(expensive, 10)
        response = self.client.post(url, {'doctor_id': expensive.pk}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((response.data['slot'], response.data['status'], response.data['amount']), (target.pk, 'confirmed', 200))
        self.assertEqual(response.data['doctor_name'], 'Dr. Ananya doc3')
        self.assertEqual(Consultation.objects.get(pk=response.data['consultation']).doctor, expensive)
        self.assertEqual(self.client.post(url, {'doctor_id': self.doctor.pk}, format='json').status_code, 200)

    def test_assign_without_doctor_slot_and_rejects_double_booking(self):
        first = self.submit(self.draft(), self.at(10)).data['id']
        other = User.objects.create_user(username='other', role='patient')
        second = self.submit(self.draft(user=other), self.at(10)).data['id']
        self.pay(first)
        self.pay(second)
        response = self.assign(first, self.doctor)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data['slot'])
        clash = self.assign(second, self.doctor)
        self.assertEqual(clash.status_code, 400)
        self.assertIn('already has an appointment', str(clash.data))
        self.assertEqual(self.assign(second, self.doctor2).status_code, 200)


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'], PUSH_NOTIFICATIONS_ENABLED=False)
class AppointmentAssignmentAdminTests(HomeTestBase):
    def setUp(self):
        super().setUp()
        self.appointment = self.book_and_pay()
        self.admin_user = User.objects.create_superuser(
            username='assignment_admin', password='unused-test-password', email='admin@example.com',
        )
        self.admin_login()

    def admin_login(self):
        self.client.force_authenticate(user=None)
        self.client.force_login(self.admin_user)

    def change_url(self):
        return f'/admin/appointments/appointment/{self.appointment.pk}/change/'

    def payload(self, starts_at, doctor):
        data = {
            'doctor': doctor.pk, 'slot_time_0': timezone.localtime(starts_at).date().isoformat(),
            'slot_time_1': timezone.localtime(starts_at).strftime('%H:%M:%S'),
            'calls-TOTAL_FORMS': '0', 'calls-INITIAL_FORMS': '0',
        }
        for field in ('paid_at', 'doctor_assigned_at', 'cancelled_at', 'reminder_sent_at'):
            value = getattr(self.appointment, field)
            local = timezone.localtime(value) if value else None
            data[f'{field}_0'] = local.date().isoformat() if local else ''
            data[f'{field}_1'] = local.strftime('%H:%M:%S') if local else ''
        return data

    def test_admin_can_assign_doctor_and_replacement_time(self):
        page = self.client.get(self.change_url())
        form = page.context['adminform'].form
        self.assertIn('doctor', form.fields)
        self.assertIn('slot_time', form.fields)
        slot = self.slot(self.doctor, 0)
        response = self.client.post(self.change_url(), self.payload(self.at(0), self.doctor))
        self.assertEqual(response.status_code, 302, response.context and response.context['adminform'].form.errors)
        self.appointment.refresh_from_db()
        self.appointment.consultation.refresh_from_db()
        self.assertEqual(self.appointment.doctor_id, self.doctor.pk)
        self.assertEqual(self.appointment.slot_time, self.at(0))
        self.assertEqual(self.appointment.consultation.scheduled_at, self.at(0))
        self.assertEqual(self.appointment.slot_id, slot.pk)
        self.assertEqual(self.appointment.status, 'confirmed')
        self.assertEqual(Notification.objects.filter(appointment=self.appointment, kind='doctor_assigned').count(), 1)
        self.assertEqual(Notification.objects.filter(appointment=self.appointment, kind='appointment_assigned').count(), 1)

    def test_admin_rejects_conflict_invalid_time_and_missing_payment_as_form_errors(self):
        busy = self.book_and_pay(hour=11)
        self.assertEqual(self.assign(busy, self.doctor).status_code, 200)
        self.admin_login()
        for at in (self.at(11), self.at(10, 7)):
            response = self.client.post(self.change_url(), self.payload(at, self.doctor))
            self.assertEqual(response.status_code, 200)
            errors = response.context['adminform'].form.errors
            if at == self.at(11):
                self.assertIn('Doctor already has an appointment at this time.', errors['doctor'])
            else:
                self.assertIn('Choose a 15-minute time, e.g. 10:00 or 10:15.', errors['slot_time'])
            self.appointment.refresh_from_db()
            self.assertEqual(self.appointment.status, 'finding_doctor')
            self.assertEqual(self.appointment.slot_time, self.at(10))
            self.assertIsNone(self.appointment.doctor_id)
        Payment.objects.filter(consultation=self.appointment.consultation).update(status='pending')
        response = self.client.post(self.change_url(), self.payload(self.at(12), self.doctor))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Confirmed payment is required.', response.context['adminform'].form.non_field_errors())
        self.assertFalse(Notification.objects.filter(appointment=self.appointment, kind='doctor_assigned').exists())

    def test_admin_can_edit_confirmed_assignment_then_locks_after_credentials(self):
        self.assertEqual(self.assign(self.appointment, self.doctor).status_code, 200)
        self.appointment.refresh_from_db()
        self.admin_login()
        page = self.client.get(self.change_url())
        form = page.context['adminform'].form
        self.assertIn('doctor', form.fields)
        self.assertIn('slot_time', form.fields)
        other = self.make_doctor('another_doc')
        response = self.client.post(self.change_url(), self.payload(self.at(12), other))
        self.assertEqual(response.status_code, 302, response.context and response.context['adminform'].form.errors)
        self.appointment.refresh_from_db()
        self.appointment.consultation.refresh_from_db()
        self.assertEqual(self.appointment.doctor_id, other.pk)
        self.assertEqual(self.appointment.slot_time, self.at(12))
        self.assertEqual(self.appointment.consultation.doctor_id, other.pk)
        self.assertEqual(self.appointment.consultation.scheduled_at, self.at(12))
        AppointmentVideoRoom.objects.create(appointment=self.appointment, template_id='template', room_id='room')
        page = self.client.get(self.change_url())
        self.assertNotIn('doctor', page.context['adminform'].form.fields)
        self.assertContains(page, 'Issued video join credentials forbid rescheduling')
        response = self.client.post(self.change_url(), self.payload(self.at(13), self.doctor))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Issued video join credentials', str(response.context['adminform'].form.non_field_errors()))
        self.appointment.refresh_from_db()
        self.assertEqual((self.appointment.doctor_id, self.appointment.slot_time), (other.pk, self.at(12)))
