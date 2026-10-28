from rest_framework.test import APITestCase

from .models import DoctorApplication
from .serializers import DoctorApplicationSubmissionSerializer


class DoctorApplicationOptionalFieldsTests(APITestCase):
    url = '/api/v1/doctors/applications/'

    def test_three_field_form_is_saved(self):
        response = self.client.post(self.url, {
            'full_name': 'Dr. Test', 'phone_number': '9876543210', 'qualification': 'MBBS',
        }, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        application = DoctorApplication.objects.get(pk=response.data['id'])
        self.assertEqual(
            (application.full_name, application.phone_number, application.qualification),
            ('Dr. Test', '9876543210', 'MBBS'),
        )
        self.assertIsNone(application.experience_years)
        self.assertIsNone(application.consultation_fee)
        self.assertEqual(application.consultation_category, '')
        self.assertEqual(application.treatment_systems, [])
        self.assertEqual(application.status, DoctorApplication.Status.PENDING)

    def test_all_fields_can_be_omitted(self):
        response = self.client.post(self.url, {}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['full_name'], '')
        self.assertIsNone(response.data['consultation_fee'])
        self.assertIsNone(response.data['experience_years'])

    def test_explicit_blank_fields_are_accepted(self):
        fields = {
            'full_name': '', 'phone_number': '', 'qualification': '', 'email': '', 'specialization': '',
            'consultation_category': '', 'consultation_fee': '', 'experience_years': '',
            'country_code': '', 'city': '', 'message': '',
        }
        response = self.client.post(self.url, fields, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['country_code'], 'IN')
        schema = DoctorApplicationSubmissionSerializer(data={**fields, 'experience_years': None, 'consultation_fee': None, 'treatment_systems': []})
        self.assertTrue(schema.is_valid(), schema.errors)

    def test_each_field_is_independently_optional(self):
        for fields in [
            {'qualification': 'MBBS'}, {'experience_years': 0},
            {'consultation_category': 'general'}, {'consultation_category': 'specialist'},
            {'consultation_fee': 500},
        ]:
            with self.subTest(fields=fields):
                response = self.client.post(self.url, fields, format='multipart')
                self.assertEqual(response.status_code, 201, response.data)

    def test_supplied_invalid_fields_still_fail(self):
        for fields in [
            {'experience_years': -1}, {'consultation_fee': 0}, {'email': 'not-an-email'},
            {'consultation_category': 'unknown'}, {'treatment_systems': ['unknown']},
            {'consultation_category': 'specialist', 'consultation_fee': 201},
            {'consultation_category': 'general', 'consultation_fee': 500},
        ]:
            with self.subTest(fields=fields):
                self.assertEqual(self.client.post(self.url, fields, format='multipart').status_code, 400)
        self.assertFalse(DoctorApplication.objects.exists())

    def test_approved_sparse_application_can_be_listed(self):
        application = DoctorApplication.objects.create(
            full_name='Dr. Test', qualification='MBBS', status=DoctorApplication.Status.APPROVED,
        )
        response = self.client.get('/api/v1/doctors/featured/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data[0]['id'], application.pk)
        self.assertIsNone(response.data[0]['experience_years'])
        self.assertIsNone(response.data[0]['consultation_fee'])
        self.assertIsNone(response.data[0]['fee_display'])
