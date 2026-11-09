from django.contrib.auth import get_user_model

from apps.appointments.models import Appointment
from apps.doctors.models import Speciality
from apps.notifications.tests import HomeTestBase
from .models import Condition, ConditionType, ConditionVariant

User = get_user_model()


class SpecialityMappingTests(HomeTestBase):
    """Patients never pick a speciality: it follows the disease/type chosen in the Symptoms step."""

    def setUp(self):
        super().setUp()
        self.neuro = Speciality.objects.create(name='Neurology (test)', slug='neurology-test', fee=600)
        self.headache = Condition.objects.create(name='Head pain (test)', slug='head-pain-test', speciality=self.derma)
        self.cluster = ConditionType.objects.create(condition=self.headache, name='Cluster', speciality=self.neuro)
        self.tension = ConditionType.objects.create(condition=self.headache, name='Tension')
        self.chronic = ConditionVariant.objects.create(condition_type=self.cluster, name='Chronic')
        self.unmapped = Condition.objects.create(name='Unmapped (test)', slug='unmapped-test')

    def history(self, consultation_id, **choice):
        return self.client.put(f'/api/v1/consultations/{consultation_id}/history/', {
            **choice, 'duration_value': 2, 'duration_unit': 'days', 'ongoing_medication': False,
        }, format='json')

    def test_step1_ignores_speciality(self):
        self.client.force_authenticate(self.patient)
        response = self.client.post('/api/v1/consultations/', {
            'patient_name': 'A', 'patient_age': 25, 'patient_gender': 'male', 'mode': 'video', 'speciality': self.derma.pk,
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data['speciality'])
        self.assertEqual(response.data['consultation_title'], 'General Consultation')
        response = self.client.patch(f'/api/v1/consultations/{response.data["id"]}/', {'speciality': self.derma.pk}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data['speciality'])

    def test_type_overrides_disease_then_falls_back(self):
        consultation_id = self.draft(history=False)
        response = self.history(
            consultation_id, condition=self.headache.pk, condition_type=self.cluster.pk, condition_variant=self.chronic.pk,
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((response.data['speciality'], response.data['fee'], response.data['fee_currency']), (self.neuro.pk, 600, 'INR'))

        response = self.history(consultation_id, condition=self.headache.pk, condition_type=self.tension.pk)
        self.assertEqual((response.data['speciality'], response.data['consultation_title']), (self.derma.pk, 'Skin Consultation'))

        response = self.history(consultation_id, condition=self.unmapped.pk)
        self.assertEqual((response.data['speciality'], response.data['fee'], response.data['consultation_title']), (None, 200, 'General Consultation'))

        response = self.history(consultation_id)
        self.assertIsNone(response.data['speciality'])

    def test_inactive_speciality_is_skipped(self):
        consultation_id = self.draft(history=False)
        self.neuro.is_active = False
        self.neuro.save()
        response = self.history(
            consultation_id, condition=self.headache.pk, condition_type=self.cluster.pk, condition_variant=self.chronic.pk,
        )
        self.assertEqual(response.data['speciality'], self.derma.pk)
        self.derma.is_active = False
        self.derma.save()
        response = self.history(
            consultation_id, condition=self.headache.pk, condition_type=self.cluster.pk, condition_variant=self.chronic.pk,
        )
        self.assertIsNone(response.data['speciality'])

    def test_mapped_booking_is_charged_and_assigned_by_speciality(self):
        consultation_id = self.draft(history=False)
        self.history(consultation_id, condition=self.headache.pk, condition_type=self.tension.pk)
        response = self.submit(consultation_id, self.at(10))
        self.assertEqual(response.status_code, 201, response.data)
        appointment = Appointment.objects.get(pk=response.data['id'])
        self.assertEqual((appointment.consultation.speciality, appointment.consultation.fee_charged), (self.derma, 400))

    def test_conditions_list_shows_resolved_speciality(self):
        self.make_doctor('derm-a', speciality=self.derma, fee=450)
        self.client.force_authenticate(self.patient)
        # 3 for the tree, plus one fee lookup per distinct speciality (Dermatology is used twice but computed once).
        with self.assertNumQueries(5):
            data = self.client.get('/api/v1/consultations/conditions/').data
        headache = next(item for item in data if item['id'] == self.headache.pk)
        self.assertEqual(headache['speciality'], {
            'id': self.derma.pk, 'name': 'Dermatology (test)', 'slug': 'dermatology-test', 'title': 'Skin Consultation',
            'fee': 450, 'currency': 'INR', 'fee_display': '\u20b9450',
        })
        types = {item['name']: item['speciality'] for item in headache['types']}
        self.assertEqual(types['Cluster']['id'], self.neuro.pk)
        self.assertEqual(types['Tension']['id'], self.derma.pk)
        self.assertIsNone(next(item for item in data if item['id'] == self.unmapped.pk)['speciality'])
