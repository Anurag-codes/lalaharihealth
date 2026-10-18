from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.consultations.models import Consultation
from apps.doctors.models import DoctorProfile
from apps.payments.models import Payment
from apps.treatments.models import Condition
from .availability import local_datetime
from .models import Appointment, AppointmentSlot

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

    def submit(self, consultation_id, slot_id, confirmed=True):
        return self.client.post(
            '/api/v1/appointments/',
            {'consultation_id': consultation_id, 'slot_id': slot_id, 'information_confirmed': confirmed}, format='json',
        )

    # Symptoms dropdowns

    def test_condition_tree_and_history_hierarchy(self):
        self.client.force_authenticate(self.patient)
        response = self.client.get('/api/v1/consultations/conditions/', {'page_size': 100})
        self.assertEqual(response.status_code, 200)
        headache = next(item for item in response.data['results'] if item['name'] == 'Headache')
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
            {'date': self.day.isoformat(), 'start_time': '07:45'},
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
        self.assertEqual(self.submit(self.draft(), booked.pk).status_code, 201)
        self.client.force_authenticate(self.doctor)
        listing = self.client.get('/api/v1/doctors/me/slots/', {'date': self.day.isoformat()}).data
        self.assertTrue(listing[0]['is_booked'])
        self.assertEqual(self.client.delete(f'/api/v1/doctors/me/slots/{booked.pk}/').status_code, 400)
        self.assertEqual(self.client.delete(f'/api/v1/doctors/me/slots/{foreign.pk}/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/v1/doctors/me/slots/{free.pk}/').status_code, 204)
        self.assertFalse(AppointmentSlot.objects.filter(pk=free.pk).exists())

    # Patient Schedule Appointment

    def test_patient_sees_each_time_once_from_verified_doctors(self):
        self.slot(self.doctor, 10)
        self.slot(self.doctor2, 10)
        self.slot(self.doctor, 10, 15)
        self.slot(self.make_doctor('pending', verified=False), 11)
        self.client.force_authenticate(self.patient)
        response = self.client.get('/api/v1/appointments/slots/', {'date': self.day.isoformat()})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([(item['time_display'], item['remaining_capacity']) for item in response.data], [('10:00 AM', 2), ('10:15 AM', 1)])
        dates = self.client.get('/api/v1/appointments/slot-dates/', {'days': 7}).data
        self.assertEqual(len(dates), 7)
        self.assertEqual(dates[0]['day_label'], 'Today')
        self.assertEqual(dates[2]['available_slot_count'], 2)
        self.assertEqual(dates[1]['available_slot_count'], 0)

    # Case Preview and Submit Case

    def test_case_preview_then_submit_requires_confirmation(self):
        slot = self.slot(self.doctor, 19)
        consultation_id = self.draft()
        response = self.client.get(f'/api/v1/consultations/{consultation_id}/preview/', {'slot_id': slot.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['ready_to_submit'])
        self.assertEqual(response.data['chief_complaint'], 'General Consultation')
        self.assertEqual(response.data['schedule']['time_display'], '07:00 PM')
        self.assertEqual(response.data['patient']['relation_label'], 'You')
        self.assertEqual(response.data['duration_display'], '5 Days')
        self.assertEqual((response.data['fee'], response.data['document_count']), (200, 0))
        self.assertFalse(Appointment.objects.exists())

        self.assertEqual(self.submit(consultation_id, slot.pk, confirmed=False).status_code, 400)
        response = self.submit(consultation_id, slot.pk)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual((response.data['schedule_time'], response.data['amount']), ('07:00 PM', 200))
        self.assertEqual(response.data['appointment_number'], f'APT-{response.data["id"]:05d}')
        self.assertIsNotNone(Consultation.objects.get(pk=consultation_id).information_confirmed_at)
        preview = self.client.get(f'/api/v1/consultations/{consultation_id}/preview/').data
        self.assertFalse(preview['ready_to_submit'])

    def test_preview_flags_missing_steps(self):
        self.client.force_authenticate(self.patient)
        details = {'patient_name': 'Rahul Sharma', 'patient_age': 25, 'patient_gender': 'male', 'patient_phone': '9876543210'}
        consultation_id = self.client.post('/api/v1/consultations/', details, format='json').data['id']
        response = self.client.get(f'/api/v1/consultations/{consultation_id}/preview/')
        self.assertEqual(response.data['missing_steps'], ['history', 'schedule'])
        self.assertFalse(response.data['ready_to_submit'])

    def test_taken_slot_falls_back_to_another_doctor_at_same_time(self):
        first = self.slot(self.doctor, 10)
        self.slot(self.doctor2, 10)
        self.assertEqual(self.submit(self.draft(), first.pk).status_code, 201)
        other = User.objects.create_user(username='other', role='patient')
        response = self.submit(self.draft(user=other), first.pk)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotEqual(response.data['slot'], first.pk)
        third = User.objects.create_user(username='third', role='patient')
        consultation_id = self.draft(user=third)
        preview = self.client.get(f'/api/v1/consultations/{consultation_id}/preview/', {'slot_id': first.pk}).data
        self.assertFalse(preview['schedule']['is_available'])
        self.assertEqual(self.submit(consultation_id, first.pk).status_code, 400)

    # Staff matching after payment

    def test_assign_doctor_moves_booking_to_that_doctors_slot(self):
        slot = self.slot(self.doctor, 10)
        target = self.slot(self.doctor2, 10)
        appointment_id = self.submit(self.draft(), slot.pk).data['id']
        appointment = Appointment.objects.get(pk=appointment_id)
        appointment.status = Appointment.Status.FINDING_DOCTOR
        appointment.save(update_fields=['status'])
        Payment.objects.create(user=self.patient, consultation=appointment.consultation, amount=200, status=Payment.Status.SUCCESS)
        self.client.force_authenticate(User.objects.create_user(username='staff', is_staff=True))
        no_slot = self.make_doctor('doc3')
        url = f'/api/v1/appointments/{appointment_id}/assign-doctor/'
        self.assertEqual(self.client.post(url, {'doctor_id': no_slot.pk}, format='json').status_code, 400)
        response = self.client.post(url, {'doctor_id': self.doctor2.pk}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((response.data['slot'], response.data['status']), (target.pk, 'confirmed'))
        self.assertEqual(response.data['doctor_name'], 'Dr. Ananya doc2')

        self.client.force_authenticate(self.patient)
        free = self.client.get('/api/v1/appointments/slots/', {'date': self.day.isoformat()}).data
        self.assertEqual(free, [{'id': slot.pk, 'starts_at': free[0]['starts_at'], 'time_display': '10:00 AM', 'remaining_capacity': 1}])
