from rest_framework.test import APITestCase

from .models import HospitalApplication
from .serializers import HospitalApplicationSubmissionSerializer


class HospitalApplicationOptionalFieldsTests(APITestCase):
    url = '/api/v1/hospitals/applications/'

    def test_three_field_form_is_saved(self):
        fields = {
            'facility_name': 'Test Lab', 'phone_number': '9876543210', 'contact_person_name': 'Test Owner',
        }
        response = self.client.post(self.url, fields, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        application = HospitalApplication.objects.get(pk=response.data['id'])
        for name, value in fields.items():
            self.assertEqual(getattr(application, name), value)
        self.assertEqual(application.city, '')
        self.assertIsNone(application.bed_count)
        self.assertEqual(application.status, HospitalApplication.Status.PENDING)

    def test_all_fields_can_be_omitted_or_blank(self):
        for fields in [{}, {
            'facility_name': '', 'contact_person_name': '', 'phone_number': '', 'email': '', 'city': '',
            'address': '', 'specialties': '', 'bed_count': '', 'message': '',
        }]:
            with self.subTest(fields=fields):
                response = self.client.post(self.url, fields, format='multipart')
                self.assertEqual(response.status_code, 201, response.data)
                self.assertIsNone(response.data['bed_count'])
        serializer = HospitalApplicationSubmissionSerializer(data={})
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_supplied_invalid_fields_still_fail(self):
        for fields in [{'email': 'not-an-email'}, {'bed_count': -1}]:
            with self.subTest(fields=fields):
                self.assertEqual(self.client.post(self.url, fields, format='multipart').status_code, 400)
        self.assertFalse(HospitalApplication.objects.exists())

    def test_existing_full_form_remains_supported(self):
        fields = {
            'facility_name': 'Test Clinic', 'phone_number': '9876543210', 'contact_person_name': 'Test Owner',
            'email': 'test@example.com', 'city': 'Delhi', 'address': 'Test Road', 'specialties': 'Cardiology',
            'bed_count': 10, 'message': 'Please call',
        }
        response = self.client.post(self.url, fields, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        for name, value in fields.items():
            self.assertEqual(response.data[name], value)
