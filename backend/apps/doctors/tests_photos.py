from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from .models import DoctorApplication


def image_upload(name='photo.png', image_format='PNG'):
    buffer = BytesIO()
    Image.new('RGB', (8, 8), 'teal').save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f'image/{image_format.lower()}')


class DoctorApplicationPhotoTests(APITestCase):
    url = '/api/v1/doctors/applications/'
    base = {
        'full_name': 'Dr. Ananya Sharma', 'phone_number': '9876543210', 'qualification': 'MBBS', 'experience_years': 5,
        'specialization': 'General Physician', 'treatment_systems': ['allopathy'],
        'consultation_category': 'general', 'consultation_fee': 200,
    }

    def setUp(self):
        media = TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings_override = override_settings(MEDIA_ROOT=media.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)

    def apply(self, **fields):
        return self.client.post(self.url, {**self.base, **fields}, format='multipart')

    def test_photo_is_optional(self):
        response = self.apply()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data['photo'])

    def test_photo_upload_for_general_and_specialist(self):
        general = self.apply(photo=image_upload('me.png'))
        self.assertEqual(general.status_code, 201, general.data)
        self.assertRegex(general.data['photo'], r'^http://testserver/media/doctor_applications/photos/[0-9a-f]{32}\.png$')

        specialist = self.apply(
            consultation_category='specialist', consultation_fee=500, specialization='Dermatologist',
            photo=image_upload('me.jpg', 'JPEG'),
        )
        self.assertEqual(specialist.status_code, 201, specialist.data)
        self.assertTrue(DoctorApplication.objects.get(pk=specialist.data['id']).photo.name.endswith('.jpg'))

    def test_rejects_fake_wrong_format_and_oversized_photos(self):
        fake = SimpleUploadedFile('me.png', b'%PDF-1.4 not an image', content_type='image/png')
        self.assertEqual(self.apply(photo=fake).status_code, 400)
        gif = self.apply(photo=image_upload('me.gif', 'GIF'))
        self.assertEqual(gif.status_code, 400)
        self.assertIn('JPG, PNG or WEBP', str(gif.data['photo']))
        with patch('apps.doctors.serializers.MAX_PHOTO_BYTES', 10):
            self.assertIn('5 MB', str(self.apply(photo=image_upload()).data['photo']))
        self.assertFalse(DoctorApplication.objects.exists())


class FeaturedDoctorTests(APITestCase):
    url = '/api/v1/doctors/featured/'

    def make(self, name, status, **fields):
        return DoctorApplication.objects.create(
            full_name=name, phone_number='9876543210', email=f'{name.split()[-1].lower()}@gmail.com',
            qualification='MBBS', experience_years=7, specialization='General Physician',
            treatment_systems=['allopathy'], status=status, **fields,
        )

    def test_lists_only_approved_doctors_newest_first(self):
        self.make('Dr. Pending', DoctorApplication.Status.PENDING)
        self.make('Dr. Contacted', DoctorApplication.Status.CONTACTED)
        self.make('Dr. Rejected', DoctorApplication.Status.REJECTED)
        self.make('Dr. First', DoctorApplication.Status.APPROVED)
        self.make('Dr. Second', DoctorApplication.Status.APPROVED, consultation_category='specialist', consultation_fee=500)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([doctor['name'] for doctor in response.data], ['Dr. Second', 'Dr. First'])
        self.assertEqual((response.data[0]['fee_display'], response.data[0]['photo_url']), ('\u20b9500', None))

    def test_never_exposes_contact_details_or_documents(self):
        self.make('Dr. Private', DoctorApplication.Status.APPROVED, city='Delhi', message='Call me after 6')
        doctor = self.client.get(self.url).data[0]
        self.assertEqual(set(doctor), {
            'id', 'name', 'qualification', 'specialization', 'experience_years', 'consultation_category',
            'treatment_systems', 'consultation_fee', 'currency', 'fee_display', 'photo_url',
        })

    def test_photo_url_is_absolute(self):
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            application = self.make('Dr. Photo', DoctorApplication.Status.APPROVED)
            application.photo.save('face.png', image_upload(), save=True)
            photo_url = self.client.get(self.url).data[0]['photo_url']
        self.assertTrue(photo_url.startswith('http://testserver/media/doctor_applications/photos/'))

    def test_empty_when_nobody_is_approved(self):
        self.make('Dr. Pending', DoctorApplication.Status.PENDING)
        self.assertEqual(self.client.get(self.url).data, [])
