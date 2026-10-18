import io
import tempfile
from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment
from apps.consultations.models import Consultation, ConsultationDocument, PrescriptionItem
from apps.doctors.models import DoctorProfile
from .models import FamilyMember, PatientProfile, years_since

User = get_user_model()


def png_bytes():
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), 'red').save(buffer, format='PNG')
    return buffer.getvalue()


def birth_date(age):
    return date(date.today().year - age, 1, 1)


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ProfileApiTestBase(APITestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username='patient', role='patient', first_name='Rahul', last_name='Sharma',
            phone_number='+919876543210', email='rahul@example.com',
        )
        self.other = User.objects.create_user(username='other', role='patient')
        self.client.force_authenticate(self.patient)
        self.storage_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage_directory.cleanup)
        storage = FileSystemStorage(location=self.storage_directory.name)
        for field in [PatientProfile._meta.get_field('profile_photo'), ConsultationDocument._meta.get_field('file')]:
            storage_patch = patch.object(field, 'storage', storage)
            storage_patch.start()
            self.addCleanup(storage_patch.stop)

    def add_member(self, owner=None, **overrides):
        data = {
            'owner': owner or self.patient, 'full_name': 'Priya Sharma', 'relation': 'spouse',
            'date_of_birth': birth_date(33), 'gender': 'female', 'phone_number': '+919876543211',
        }
        data.update(overrides)
        return FamilyMember.objects.create(**data)

    def make_doctor(self, username='doctor', verified=True):
        doctor = User.objects.create_user(username=username, role='doctor', first_name='Ananya', last_name='Sharma')
        DoctorProfile.objects.create(
            user=doctor, specialization='General Physician', systems_practiced='allopathy', qualification='MBBS',
            registration_number=f'REG-{username}', consultation_fee=200,
            verification_status='verified' if verified else 'pending',
        )
        return doctor

    def booking(self, doctor=None, appointment_status='confirmed', member=None, owner=None, days=1, **fields):
        owner = owner or self.patient
        slot_time = timezone.now() + timedelta(days=days)
        consultation = Consultation.objects.create(
            patient=owner, doctor=doctor, family_member=member,
            patient_relation=member.relation if member else 'self',
            patient_name=member.full_name if member else 'Rahul Sharma',
            patient_age=member.age if member else 35, patient_gender='female' if member else 'male',
            patient_phone='9876543210', mode='video', status=fields.pop('status', 'requested'),
            scheduled_at=slot_time, symptoms='Fever', **fields,
        )
        Appointment.objects.create(
            consultation=consultation, patient=owner, doctor=doctor, slot_time=slot_time, status=appointment_status,
        )
        return consultation


class PatientProfileTests(ProfileApiTestBase):
    def test_profile_screen_data(self):
        self.add_member()
        self.add_member(full_name='Aarav', relation='son', date_of_birth=birth_date(9), gender='male')
        response = self.client.get('/api/v1/patients/profile/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response.data['full_name'], 'Rahul Sharma')
        self.assertEqual(response.data['phone_number'], '+919876543210')
        self.assertEqual(response.data['membership_label'], 'LalaHari Health Beneficiary')
        self.assertEqual(response.data['family_member_count'], 2)
        self.assertEqual(response.data['preferred_language'], 'en')
        self.assertEqual([item['code'] for item in response.data['available_languages']], ['en', 'hi'])
        self.assertIsNone(response.data['photo_url'])

    def test_update_profile_and_language(self):
        response = self.client.patch('/api/v1/patients/profile/', {
            'first_name': 'Rahul K', 'city': 'Delhi', 'gender': 'male', 'date_of_birth': '1990-05-14',
            'preferred_language': 'hi',
        }, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['preferred_language_label'], 'हिन्दी')
        self.assertEqual(response.data['age'], years_since(date(1990, 5, 14)))
        self.patient.refresh_from_db()
        self.assertEqual((self.patient.first_name, self.patient.city), ('Rahul K', 'Delhi'))
        self.assertEqual(self.patient.patient_profile.preferred_language, 'hi')

    def test_rejects_unknown_language_read_only_fields_and_future_birth_date(self):
        self.assertEqual(self.client.patch('/api/v1/patients/profile/', {'preferred_language': 'fr'}, format='json').status_code, 400)
        response = self.client.patch('/api/v1/patients/profile/', {'phone_number': '+910000000000', 'email': 'x@example.com'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.data), {'email', 'phone_number'})
        future = (date.today() + timedelta(days=1)).isoformat()
        self.assertEqual(self.client.patch('/api/v1/patients/profile/', {'date_of_birth': future}, format='json').status_code, 400)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.phone_number, '+919876543210')

    def test_photo_upload_download_replace_and_delete(self):
        upload = SimpleUploadedFile('me.png', png_bytes(), content_type='image/png')
        response = self.client.put('/api/v1/patients/profile/photo/', {'photo': upload}, format='multipart')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data['photo_url'].endswith('/api/v1/patients/profile/photo/'))
        first_name = PatientProfile.objects.get(user=self.patient).profile_photo.name
        download = self.client.get('/api/v1/patients/profile/photo/')
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b''.join(download.streaming_content), png_bytes())
        download.close()

        with self.captureOnCommitCallbacks(execute=True):
            replace = SimpleUploadedFile('new.png', png_bytes(), content_type='image/png')
            self.assertEqual(self.client.put('/api/v1/patients/profile/photo/', {'photo': replace}, format='multipart').status_code, 200)
        storage = PatientProfile._meta.get_field('profile_photo').storage
        self.assertFalse(storage.exists(first_name))

        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.delete('/api/v1/patients/profile/photo/').status_code, 204)
        self.assertEqual(self.client.get('/api/v1/patients/profile/photo/').status_code, 404)

    def test_photo_rejects_fake_and_oversized_images(self):
        fake = SimpleUploadedFile('me.png', b'%PDF-1.4 not an image', content_type='image/png')
        self.assertEqual(self.client.put('/api/v1/patients/profile/photo/', {'photo': fake}, format='multipart').status_code, 400)
        with patch('apps.patients.serializers.MAX_PHOTO_BYTES', 10):
            big = SimpleUploadedFile('me.png', png_bytes(), content_type='image/png')
            response = self.client.put('/api/v1/patients/profile/photo/', {'photo': big}, format='multipart')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(PatientProfile.objects.filter(user=self.patient).exclude(profile_photo='').exists())

    def test_requires_patient_account(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/v1/patients/profile/').status_code, 401)
        self.client.force_authenticate(self.make_doctor())
        self.assertEqual(self.client.get('/api/v1/patients/profile/').status_code, 403)
        self.assertEqual(self.client.get('/api/v1/patients/family-members/').status_code, 403)

    def test_support_contacts_are_public(self):
        self.client.force_authenticate(None)
        response = self.client.get('/api/v1/core/support-contacts/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['phone'], '+919818677599')
        self.assertEqual(response.data['phone_display'], '98186 77599')
        self.assertEqual(response.data['email'], 'care@lalaharihealth.com')
        self.assertEqual(response.data['email_link'], 'mailto:care@lalaharihealth.com')


class FamilyMemberTests(ProfileApiTestBase):
    def test_add_list_view_edit_remove(self):
        response = self.client.post('/api/v1/patients/family-members/', {
            'full_name': 'Priya Sharma', 'relation': 'spouse', 'date_of_birth': birth_date(33).isoformat(),
            'gender': 'female', 'phone_number': '+919876543211',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual((response.data['age'], response.data['relation_label']), (33, 'Spouse'))
        member_id = response.data['id']
        child = self.client.post('/api/v1/patients/family-members/', {
            'full_name': 'Aarav', 'relation': 'son', 'date_of_birth': birth_date(9).isoformat(), 'gender': 'male',
        }, format='json')
        self.assertEqual(child.status_code, 201, child.data)
        self.assertEqual(child.data['phone_number'], '')

        listing = self.client.get('/api/v1/patients/family-members/')
        self.assertEqual([item['full_name'] for item in listing.data], ['Priya Sharma', 'Aarav'])
        self.assertEqual(self.client.get(f'/api/v1/patients/family-members/{member_id}/').data['gender_label'], 'Female')

        edit = self.client.patch(f'/api/v1/patients/family-members/{member_id}/', {'phone_number': '+919811112222'}, format='json')
        self.assertEqual(edit.status_code, 200, edit.data)
        self.assertEqual(edit.data['phone_number'], '+919811112222')
        self.assertEqual(self.client.put(f'/api/v1/patients/family-members/{member_id}/', {}, format='json').status_code, 405)

        self.assertEqual(self.client.delete(f'/api/v1/patients/family-members/{member_id}/').status_code, 204)
        self.assertEqual(FamilyMember.objects.filter(owner=self.patient).count(), 1)

    def test_validation(self):
        bad = {
            'full_name': 'X', 'relation': 'cousin', 'date_of_birth': (date.today() + timedelta(days=2)).isoformat(),
            'gender': 'female', 'phone_number': '12ab',
        }
        response = self.client.post('/api/v1/patients/family-members/', bad, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.data), {'relation', 'date_of_birth', 'phone_number'})

    def test_members_are_owner_scoped(self):
        foreign = self.add_member(owner=self.other)
        url = f'/api/v1/patients/family-members/{foreign.pk}/'
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, {'full_name': 'Hacked'}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertEqual(self.client.get('/api/v1/patients/family-members/').data, [])

    def test_book_for_family_member_fills_details(self):
        member = self.add_member(phone_number='')
        response = self.client.post('/api/v1/consultations/', {'family_member_id': member.pk, 'mode': 'chat'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['patient_name'], 'Priya Sharma')
        self.assertEqual(response.data['patient_age'], 33)
        self.assertEqual(response.data['patient_relation'], 'spouse')
        self.assertEqual(response.data['patient_phone'], '+919876543210')
        foreign = self.add_member(owner=self.other)
        response = self.client.post('/api/v1/consultations/', {'family_member_id': foreign.pk, 'mode': 'chat'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('family_member_id', response.data)

    def test_booking_for_self_fills_known_details_and_remembers_the_rest(self):
        response = self.client.post('/api/v1/consultations/', {'mode': 'chat'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.data), {'patient_age', 'patient_gender'})
        response = self.client.post(
            '/api/v1/consultations/', {'family_member_id': None, 'patient_age': 25, 'patient_gender': 'male', 'mode': 'chat'},
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['patient_name'], 'Rahul Sharma')
        self.assertEqual(response.data['patient_phone'], '+919876543210')
        self.assertEqual(PatientProfile.objects.get(user=self.patient).gender, 'male')
        response = self.client.post('/api/v1/consultations/', {'mode': 'chat'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual((response.data['patient_age'], response.data['patient_gender']), (25, 'male'))

    def test_new_account_remembers_name_from_patient_details(self):
        self.client.force_authenticate(self.other)
        details = {'patient_name': 'Neha Verma', 'patient_age': 30, 'patient_gender': 'female', 'patient_phone': '9876500000'}
        self.assertEqual(self.client.post('/api/v1/consultations/', details, format='json').status_code, 201)
        self.other.refresh_from_db()
        self.assertEqual((self.other.first_name, self.other.last_name), ('Neha', 'Verma'))

    def test_booking_patients_lists_myself_then_family(self):
        PatientProfile.objects.create(user=self.patient, gender='male', date_of_birth=birth_date(25))
        member = self.add_member()
        self.add_member(owner=self.other, full_name='Not Mine')
        response = self.client.get('/api/v1/patients/booking-patients/')
        self.assertEqual(response.status_code, 200)
        me, spouse = response.data
        self.assertIsNone(me['family_member_id'])
        self.assertEqual(me['subtitle'], 'Myself \u00b7 25 years \u00b7 Male')
        self.assertTrue(me['details_complete'])
        self.assertEqual((spouse['family_member_id'], spouse['relation_label']), (member.pk, 'Spouse'))
        self.client.force_authenticate(self.other)
        me = self.client.get('/api/v1/patients/booking-patients/').data[0]
        self.assertFalse(me['details_complete'])


class MedicalRecordTests(ProfileApiTestBase):
    def test_list_statuses_relations_and_filters(self):
        doctor = self.make_doctor()
        member = self.add_member()
        upcoming = self.booking(doctor=doctor, member=member, days=3)
        completed = self.booking(doctor=doctor, appointment_status='completed', status='completed', days=-2)
        cancelled = self.booking(appointment_status='cancelled', status='cancelled', days=-5)
        Consultation.objects.create(patient=self.patient, patient_name='Draft', mode='chat')
        self.booking(owner=self.other)

        response = self.client.get('/api/v1/patients/medical-records/')
        self.assertEqual(response.status_code, 200)
        rows = {row['id']: row for row in response.data['results']}
        self.assertEqual(set(rows), {upcoming.pk, completed.pk, cancelled.pk})
        self.assertEqual(rows[upcoming.pk]['status'], 'upcoming')
        self.assertEqual(rows[upcoming.pk]['patient']['relation_label'], 'Spouse')
        self.assertFalse(rows[upcoming.pk]['patient']['is_self'])
        self.assertEqual(rows[completed.pk]['status'], 'completed')
        self.assertEqual(rows[completed.pk]['doctor'], {'id': doctor.pk, 'name': 'Dr. Ananya Sharma', 'specialization': 'General Physician'})
        self.assertEqual(rows[cancelled.pk]['status'], 'cancelled')
        self.assertIsNone(rows[cancelled.pk]['doctor'])
        self.assertEqual(rows[completed.pk]['mode_label'], 'Online')

        own = self.client.get('/api/v1/patients/medical-records/?family_member_id=self').data['results']
        self.assertEqual({row['id'] for row in own}, {completed.pk, cancelled.pk})
        family = self.client.get(f'/api/v1/patients/medical-records/?family_member_id={member.pk}').data['results']
        self.assertEqual([row['id'] for row in family], [upcoming.pk])
        self.assertEqual(self.client.get('/api/v1/patients/medical-records/?family_member_id=x').data['count'], 0)

    def test_record_hidden_until_doctor_completes_and_survives_member_removal(self):
        doctor = self.make_doctor()
        member = self.add_member()
        consultation = self.booking(doctor=doctor, member=member, diagnosis='Draft diagnosis', record_updated_at=timezone.now())
        PrescriptionItem.objects.create(
            consultation=consultation, medicine_name='Azithromycin 500mg', dosage='1 tablet',
            timings=['morning'], food_relation='after_food', duration_days=5,
        )
        url = f'/api/v1/patients/medical-records/{consultation.pk}/'
        hidden = self.client.get(url).data
        self.assertFalse(hidden['has_clinical_record'])
        self.assertEqual((hidden['diagnosis'], hidden['prescriptions'], hidden['follow_up']), ('', [], None))

        Consultation.objects.filter(pk=consultation.pk).update(status='completed', follow_up_notes='After a week')
        member.delete()
        record = self.client.get(url).data
        self.assertTrue(record['has_clinical_record'])
        self.assertEqual(record['diagnosis'], 'Draft diagnosis')
        self.assertEqual(record['prescriptions'][0]['timing_labels'], ['Morning'])
        self.assertEqual(record['prescriptions'][0]['food_relation_label'], 'After food')
        self.assertEqual(record['follow_up'], {'date': None, 'notes': 'After a week'})
        self.assertEqual((record['patient']['name'], record['patient']['relation_label']), ('Priya Sharma', 'Spouse'))
        self.assertIsNone(record['patient']['family_member_id'])

    def test_other_patients_records_are_not_found(self):
        foreign = self.booking(owner=self.other)
        self.assertEqual(self.client.get(f'/api/v1/patients/medical-records/{foreign.pk}/').status_code, 404)


class DoctorRecordTests(ProfileApiTestBase):
    payload = {
        'diagnosis': 'Acute pharyngitis',
        'prescriptions': [
            {'medicine_name': 'Azithromycin 500mg', 'dosage': '1 tablet', 'timings': ['morning'],
             'food_relation': 'after_food', 'duration_days': 5},
            {'medicine_name': 'Cough syrup', 'dosage': '10 ml', 'timings': ['night', 'morning'],
             'food_relation': 'after_food', 'duration_days': 7, 'instructions': 'Shake well'},
        ],
        'doctor_notes': 'Rest well.', 'follow_up_date': '2030-01-10', 'follow_up_notes': 'Review after a week.',
        'mark_completed': True,
    }

    def setUp(self):
        super().setUp()
        self.doctor = self.make_doctor()
        self.consultation = self.booking(doctor=self.doctor)
        self.url = f'/api/v1/doctors/me/consultations/{self.consultation.pk}/record/'
        self.client.force_authenticate(self.doctor)

    def test_doctor_writes_and_completes_record(self):
        listing = self.client.get('/api/v1/doctors/me/consultations/?status=upcoming')
        self.assertEqual([row['id'] for row in listing.data['results']], [self.consultation.pk])
        self.assertEqual(self.client.get(self.url).data['symptoms'], 'Fever')

        response = self.client.put(self.url, self.payload, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(response.data['prescriptions'][1]['timings'], ['morning', 'night'])
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, 'completed')
        self.assertEqual(self.consultation.appointment.status, 'completed')
        self.assertEqual(self.client.get('/api/v1/doctors/me/consultations/?status=completed').data['count'], 1)

        corrected = {**self.payload, 'prescriptions': self.payload['prescriptions'][:1], 'mark_completed': False}
        self.assertEqual(self.client.put(self.url, corrected, format='json').status_code, 200)
        self.assertEqual(self.consultation.prescription_items.count(), 1)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.status, 'completed')

        self.client.force_authenticate(self.patient)
        record = self.client.get(f'/api/v1/patients/medical-records/{self.consultation.pk}/').data
        self.assertTrue(record['has_clinical_record'])
        self.assertEqual(record['diagnosis'], 'Acute pharyngitis')
        self.assertEqual(record['follow_up'], {'date': '2030-01-10', 'notes': 'Review after a week.'})

    def test_save_without_completing_keeps_record_private(self):
        response = self.client.put(self.url, {**self.payload, 'mark_completed': False}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['status'], 'upcoming')
        self.client.force_authenticate(self.patient)
        record = self.client.get(f'/api/v1/patients/medical-records/{self.consultation.pk}/').data
        self.assertEqual((record['diagnosis'], record['prescriptions']), ('', []))

    def test_permissions(self):
        other_doctor = self.make_doctor('other-doctor')
        unverified = self.make_doctor('new-doctor', verified=False)
        for user, expected in [(other_doctor, 404), (unverified, 403), (self.patient, 403)]:
            self.client.force_authenticate(user)
            self.assertEqual(self.client.put(self.url, self.payload, format='json').status_code, expected)
            self.assertEqual(self.client.get(self.url).status_code, expected)
        self.assertFalse(self.consultation.prescription_items.exists())

    def test_cannot_write_before_confirmation_or_after_cancellation(self):
        for appointment_status in ['finding_doctor', 'cancelled']:
            Appointment.objects.filter(consultation=self.consultation).update(status=appointment_status)
            self.assertEqual(self.client.put(self.url, self.payload, format='json').status_code, 400)
        self.consultation.refresh_from_db()
        self.assertEqual(self.consultation.diagnosis, '')

    def test_prescription_validation(self):
        bad = {**self.payload, 'prescriptions': [{
            'medicine_name': 'X', 'dosage': '1', 'timings': ['morning', 'morning'],
            'food_relation': 'sometimes', 'duration_days': 0,
        }]}
        response = self.client.put(self.url, bad, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.data['prescriptions'][0]), {'timings', 'food_relation', 'duration_days'})
        self.assertEqual(self.client.put(self.url, {**self.payload, 'diagnosis': ''}, format='json').status_code, 400)

    def test_assigned_doctor_can_download_intake_document(self):
        document = ConsultationDocument.objects.create(
            consultation=self.consultation, original_name='report.pdf',
            file=SimpleUploadedFile('report.pdf', b'%PDF-1.4 test'),
        )
        url = f'/api/v1/consultations/{self.consultation.pk}/documents/{document.pk}/download/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.client.force_authenticate(self.make_doctor('other-doctor'))
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_schema_lists_profile_endpoints(self):
        schema = self.client.get('/api/v1/schema/?format=json').data
        for path in [
            '/api/v1/patients/profile/', '/api/v1/patients/profile/photo/', '/api/v1/patients/family-members/',
            '/api/v1/patients/family-members/{member_id}/', '/api/v1/patients/medical-records/',
            '/api/v1/patients/medical-records/{consultation_id}/', '/api/v1/core/support-contacts/',
            '/api/v1/doctors/me/consultations/', '/api/v1/doctors/me/consultations/{consultation_id}/record/',
        ]:
            self.assertIn(path, schema['paths'])
        examples = schema['paths']['/api/v1/patients/family-members/']['post']['requestBody']['content']['application/json']['examples']
        self.assertIn('AddSpouse', examples)
