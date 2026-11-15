from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User, VerifiedIdentity
from apps.appointments.models import Appointment
from apps.doctors.models import DoctorProfile
from .models import Consultation, ConsultationReview


class ConsultationReviewTests(APITestCase):
    def setUp(self):
        self.patient = User.objects.create_user(username='patient', role='patient', phone_number='+919000000001')
        self.doctor = User.objects.create_user(username='doctor', role='doctor')
        self.profile = DoctorProfile.objects.create(user=self.doctor, verification_status='verified')
        self.consultation, self.appointment = self.booking()

    def booking(self, **consultation_fields):
        consultation = Consultation.objects.create(
            patient=self.patient, doctor=self.doctor, status='requested', history_completed=True,
            patient_name='Rahul', patient_phone=self.patient.phone_number, **consultation_fields,
        )
        appointment = Appointment.objects.create(
            consultation=consultation, patient=self.patient, doctor=self.doctor, status='confirmed',
            slot_time=timezone.now() - timedelta(minutes=30),
        )
        return consultation, appointment

    def url(self, consultation=None):
        return f'/api/v1/consultations/{(consultation or self.consultation).pk}/review/'

    def complete(self, appointment=None):
        Appointment.objects.filter(pk=(appointment or self.appointment).pk).update(status='completed', completed_at=timezone.now())

    def test_patient_rates_only_after_doctor_completes_and_can_edit(self):
        self.client.force_authenticate(self.patient)
        pending = self.client.get(self.url())
        self.assertEqual(pending.status_code, 200)
        self.assertFalse(pending.data['can_review'])
        self.assertEqual(self.client.put(self.url(), {'rating': 5}, format='json').status_code, 400)
        self.assertFalse(ConsultationReview.objects.exists())

        self.complete()
        saved = self.client.put(self.url(), {'rating': 5, 'feedback': '  Very helpful  '}, format='json')
        self.assertEqual(saved.status_code, 200, saved.data)
        self.assertTrue(saved.data['can_review'])
        self.assertEqual((saved.data['review']['rating'], saved.data['review']['feedback']), (5, 'Very helpful'))
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.average_rating, Decimal('5.00'))

        edited = self.client.put(self.url(), {'rating': 3}, format='json')
        self.assertEqual(edited.status_code, 200, edited.data)
        self.assertEqual((edited.data['review']['rating'], edited.data['review']['feedback']), (3, ''))
        self.assertEqual(ConsultationReview.objects.count(), 1)
        self.assertEqual(self.client.get(self.url()).data['review']['rating'], 3)

        other, other_appointment = self.booking()
        self.complete(other_appointment)
        self.assertEqual(self.client.put(self.url(other), {'rating': 4}, format='json').status_code, 200)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.average_rating, Decimal('3.50'))

    def test_rejects_invalid_input_and_unauthorized_users(self):
        self.complete()
        self.assertEqual(self.client.get(self.url()).status_code, 401)
        self.client.force_authenticate(self.doctor)
        self.assertEqual(self.client.put(self.url(), {'rating': 5}, format='json').status_code, 403)
        self.client.force_authenticate(User.objects.create_user(username='stranger', role='patient'))
        self.assertEqual(self.client.put(self.url(), {'rating': 5}, format='json').status_code, 404)
        self.client.force_authenticate(self.patient)
        for body in ({'rating': 0}, {'rating': 6}, {}, {'rating': 5, 'doctor': 9}, {'rating': 5, 'feedback': 'x' * 1001}):
            self.assertEqual(self.client.put(self.url(), body, format='json').status_code, 400, body)
        Consultation.objects.filter(pk=self.consultation.pk).update(status='cancelled')
        self.assertEqual(self.client.put(self.url(), {'rating': 5}, format='json').status_code, 400)
        self.assertFalse(ConsultationReview.objects.exists())

    def test_family_member_can_rate_but_only_one_account_owns_the_rating(self):
        spouse_phone = '+919000000002'
        consultation, appointment = self.booking(patient_relation='spouse')
        Consultation.objects.filter(pk=consultation.pk).update(patient_phone=spouse_phone)
        self.complete(appointment)
        spouse = User.objects.create_user(username='spouse', role='patient', phone_number=spouse_phone)
        VerifiedIdentity.objects.create(user=spouse, role='patient', kind='phone', value=spouse_phone)

        self.client.force_authenticate(spouse)
        self.assertEqual(self.client.put(self.url(consultation), {'rating': 4, 'feedback': 'Good'}, format='json').status_code, 200)
        self.client.force_authenticate(self.patient)
        booker_view = self.client.get(self.url(consultation))
        self.assertFalse(booker_view.data['can_review'])
        self.assertIsNone(booker_view.data['review'])
        self.assertEqual(self.client.put(self.url(consultation), {'rating': 1}, format='json').status_code, 400)
        self.assertEqual(ConsultationReview.objects.get().reviewer, spouse)
