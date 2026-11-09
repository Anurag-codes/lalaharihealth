from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment
from apps.consultations.models import Consultation
from apps.doctors.models import DoctorProfile, Speciality
from apps.notifications.models import Notification
from apps.notifications.tests import HomeTestBase
from apps.payments.gateway import record_capture
from apps.payments.models import Payment
from .models import CountryPricing
from .service import format_amount, speciality_fee, to_minor_units

User = get_user_model()

NEW_YORK = {'lat': 40.7128, 'lng': -74.006}
DELHI = {'lat': 28.6139, 'lng': 77.209}
SAO_PAULO = {'lat': -23.55, 'lng': -46.63}


def add_us():
    return CountryPricing.objects.create(
        country_code='US', country_name='United States', currency='USD', currency_symbol='$', general_fee=10,
        specialist_fee_min=10, specialist_fee_max=100, specialist_fee_step=5,
    )


class PricingApiTests(APITestCase):
    url = '/api/v1/pricing/'

    def test_india_is_the_seeded_default(self):
        data = self.client.get(self.url).data
        self.assertEqual((data['country_code'], data['currency'], data['general_fee']), ('IN', 'INR', 200))
        self.assertEqual((data['source'], data['is_fallback']), ('default', True))
        self.assertEqual(data['general_fee_display'], '\u20b9200')
        self.assertEqual(data['general_doctor_payout_display'], '\u20b9150')
        self.assertEqual(data['specialist_fee_range_display'], '\u20b9200\u2013\u20b92,000')

    def test_location_resolves_country_pricing(self):
        add_us()
        us = self.client.get(self.url, NEW_YORK).data
        self.assertEqual((us['country_code'], us['source'], us['is_fallback']), ('US', 'location', False))
        self.assertEqual((us['general_fee_display'], us['general_doctor_payout'], us['general_doctor_payout_display']), ('$10', '7.50', '$7.50'))
        india = self.client.get(self.url, DELHI).data
        self.assertEqual((india['country_code'], india['source'], india['is_fallback']), ('IN', 'location', False))

    def test_unpriced_or_inactive_country_falls_back_to_india(self):
        brazil = self.client.get(self.url, SAO_PAULO).data
        self.assertEqual((brazil['country_code'], brazil['detected_country_code'], brazil['is_fallback']), ('IN', 'BR', True))
        add_us().__class__.objects.filter(country_code='US').update(is_active=False)
        self.assertEqual(self.client.get(self.url, {'country': 'us'}).data['country_code'], 'IN')

    def test_country_query_and_validation(self):
        add_us()
        self.assertEqual(self.client.get(self.url, {'country': 'us'}).data['source'], 'country')
        self.assertEqual(self.client.get(self.url, {'lat': 10}).status_code, 400)
        self.assertEqual(self.client.get(self.url, {'lat': 91, 'lng': 0}).status_code, 400)
        self.assertEqual(self.client.get(self.url, {'country': 'USA'}).status_code, 400)

    def test_model_validation_and_formatting(self):
        bad = CountryPricing(
            country_code='ae', country_name='UAE', currency='aed', currency_symbol='AED', general_fee=40,
            specialist_fee_min=40, specialist_fee_max=95, specialist_fee_step=10,
        )
        with self.assertRaises(ValidationError):
            bad.full_clean()
        self.assertEqual((bad.country_code, bad.currency), ('AE', 'AED'))
        self.assertEqual(format_amount(40, 'AED'), 'AED 40')
        self.assertEqual((to_minor_units(10, 'USD'), to_minor_units(5, 'KWD'), to_minor_units(500, 'JPY')), (1000, 5000, 500))


class CountryBookingTests(HomeTestBase):
    def setUp(self):
        super().setUp()
        add_us()

    def us_draft(self):
        self.client.force_authenticate(self.patient)
        response = self.client.post('/api/v1/consultations/', {
            'patient_name': 'Rahul Sharma', 'patient_age': 25, 'patient_gender': 'male', 'mode': 'video', 'country_code': 'us',
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual((response.data['fee'], response.data['fee_currency'], response.data['country_code']), (10, 'USD', 'US'))
        self.client.put(
            f'/api/v1/consultations/{response.data["id"]}/history/',
            {'duration_value': 2, 'duration_unit': 'days', 'ongoing_medication': False}, format='json',
        )
        return response.data['id']

    def test_unknown_country_is_rejected(self):
        self.client.force_authenticate(self.patient)
        response = self.client.post('/api/v1/consultations/', {
            'patient_name': 'A', 'patient_age': 25, 'patient_gender': 'male', 'mode': 'video', 'country_code': 'BR',
        }, format='json')
        self.assertIn('country_code', response.data)

    def test_us_booking_is_charged_in_usd(self):
        consultation_id = self.us_draft()
        preview = self.client.get(f'/api/v1/consultations/{consultation_id}/preview/', {'starts_at': self.at(10).isoformat()}).data
        self.assertEqual((preview['fee'], preview['currency']), (10, 'USD'))
        appointment = self.submit(consultation_id, self.at(10)).data
        self.assertEqual((appointment['amount'], appointment['currency']), (10, 'USD'))

        gateway = patch('apps.payments.views.gateway_client').start()
        self.addCleanup(patch.stopall)
        gateway.return_value.order.create.return_value = {'id': 'order_us'}
        order = self.client.post('/api/v1/payments/orders/', {'appointment_id': appointment['id'], 'method': 'card'}, format='json')
        self.assertEqual(order.status_code, 200, order.data)
        self.assertEqual((order.data['amount'], order.data['currency']), (1000, 'USD'))
        sent = gateway.return_value.order.create.call_args.args[0]
        self.assertEqual((sent['amount'], sent['currency']), (1000, 'USD'))

        payment = Payment.objects.get(pk=order.data['payment_id'])
        record_capture(payment.pk, {
            'id': 'pay_us', 'order_id': 'order_us', 'amount': 1000, 'currency': 'USD', 'status': 'captured', 'method': 'card',
        })
        self.assertEqual(Appointment.objects.get(pk=appointment['id']).status, 'finding_doctor')
        self.assertIn('$10', Notification.objects.get(kind='payment_success').body)
        # A general physician from any country can take a general booking.
        self.assertEqual(self.assign(Appointment.objects.get(pk=appointment['id']), self.doctor).status_code, 200)

    def test_specialist_booking_stays_inr(self):
        self.client.force_authenticate(self.patient)
        response = self.client.post('/api/v1/consultations/', {
            'patient_name': 'A', 'patient_age': 25, 'patient_gender': 'male', 'mode': 'video', 'country_code': 'US',
        }, format='json')
        self.assertEqual((response.data['fee'], response.data['fee_currency']), (10, 'USD'))
        response = self.client.put(f'/api/v1/consultations/{response.data["id"]}/history/', {
            'condition': self.mapped_condition(self.derma).pk, 'duration_value': 2, 'duration_unit': 'days',
            'ongoing_medication': False,
        }, format='json')
        self.assertEqual((response.data['fee'], response.data['fee_currency']), (400, 'INR'))
        self.assertEqual(Consultation.objects.get(pk=response.data['id']).expected_currency, 'INR')

    def test_home_shows_local_price(self):
        self.client.force_authenticate(self.patient)
        care = self.client.get('/api/v1/patients/home/', NEW_YORK).data['general_care']
        self.assertEqual((care['country_code'], care['fee_display'], care['currency']), ('US', '$10', 'USD'))


class ConsultationFeeTests(HomeTestBase):
    url = '/api/v1/pricing/consultation-fee/'

    def fee(self, **params):
        self.client.force_authenticate(None)
        return self.client.get(self.url, params)

    def test_general_fee_comes_from_country_pricing(self):
        add_us()
        response = self.fee(category='general')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, {
            'category': 'general', 'speciality_id': None, 'speciality_name': None,
            'consultation_title': 'General Consultation', 'country_code': 'IN', 'fee': 200, 'currency': 'INR',
            'currency_symbol': '\u20b9', 'fee_display': '\u20b9200', 'source': 'general_fee',
        })
        us = self.fee(category='General', country='us').data
        self.assertEqual((us['country_code'], us['fee'], us['currency'], us['fee_display']), ('US', 10, 'USD', '$10'))
        # General doctors' own fees never change the general price.
        self.make_doctor('pricey', fee=900)
        self.make_doctor('pricey2', fee=900)
        self.assertEqual(self.fee(category='general').data['fee'], 200)

    def test_speciality_fee_is_mode_with_highest_on_tie(self):
        self.assertEqual(speciality_fee(self.derma), (400, 'speciality_fee'))
        self.make_doctor('a', speciality=self.derma, fee=300)
        self.make_doctor('b', speciality=self.derma, fee=600)
        self.assertEqual(speciality_fee(self.derma), (600, 'mode'))
        self.make_doctor('c', speciality=self.derma, fee=300)
        self.assertEqual(speciality_fee(self.derma), (300, 'mode'))
        self.make_doctor('d', speciality=self.derma, fee=600)
        self.assertEqual(speciality_fee(self.derma), (600, 'mode'))

        by_id = self.fee(category=str(self.derma.pk))
        self.assertEqual(by_id.status_code, 200, by_id.data)
        self.assertEqual(by_id.data, {
            'category': 'dermatology-test', 'speciality_id': self.derma.pk, 'speciality_name': 'Dermatology (test)',
            'consultation_title': 'Skin Consultation', 'country_code': 'IN', 'fee': 600, 'currency': 'INR',
            'currency_symbol': '\u20b9', 'fee_display': '\u20b9600', 'source': 'mode',
        })
        # Specialities are INR everywhere, so the country is ignored.
        self.assertEqual(self.fee(category='dermatology-test', country='US').data['fee'], 600)

    def test_only_active_verified_inr_doctors_count(self):
        self.make_doctor('counted', speciality=self.derma, fee=500)
        excluded = []
        for name, change in [
            ('pending', {'verification_status': 'pending'}), ('rejected', {'verification_status': 'rejected'}),
            ('inactive-profile', {'is_active': False}), ('usd', {'currency': 'USD'}), ('zero', {'consultation_fee': 0}),
        ]:
            for copy in range(2):
                doctor = self.make_doctor(f'{name}{copy}', speciality=self.derma, fee=900)
                DoctorProfile.objects.filter(user=doctor).update(**change)
                excluded.append(doctor)
        disabled = self.make_doctor('disabled', speciality=self.derma, fee=900)
        disabled2 = self.make_doctor('disabled2', speciality=self.derma, fee=900)
        User.objects.filter(pk__in=[disabled.pk, disabled2.pk]).update(is_active=False)
        other = Speciality.objects.create(name='Cardiology (test)', slug='cardiology-test', fee=800)
        self.make_doctor('cardio', speciality=other, fee=900)
        self.make_doctor('cardio2', speciality=other, fee=900)
        self.assertEqual(speciality_fee(self.derma), (500, 'mode'))
        self.assertEqual(speciality_fee(other), (900, 'mode'))

    def test_unknown_or_inactive_category_is_rejected(self):
        Speciality.objects.create(name='Hidden', slug='hidden', fee=900, is_active=False)
        for params in [{}, {'category': 'unknown'}, {'category': '99999'}, {'category': 'hidden'}, {'category': 'general', 'country': 'USA'}]:
            response = self.fee(**params)
            self.assertEqual(response.status_code, 400, params)
        self.assertIn('category', self.fee(category='hidden').data)


class DoctorApplicationPricingTests(APITestCase):
    url = '/api/v1/doctors/applications/'
    base = {
        'full_name': 'Dr. Test', 'phone_number': '9876543210', 'qualification': 'MBBS', 'experience_years': 5,
        'specialization': 'General Physician', 'treatment_systems': ['allopathy'],
    }

    def apply(self, **fields):
        return self.client.post(self.url, {**self.base, **fields}, format='multipart')

    def test_india_default_rules(self):
        self.assertEqual(self.apply(consultation_category='general', consultation_fee=200).status_code, 201)
        self.assertIn('\u20b9200', str(self.apply(consultation_category='general', consultation_fee=250).data))
        self.assertEqual(self.apply(consultation_category='specialist', consultation_fee=2100).status_code, 400)
        response = self.apply(consultation_category='specialist', consultation_fee=500)
        self.assertEqual((response.status_code, response.data['currency'], response.data['country_code']), (201, 'INR', 'IN'))

    def test_country_rules(self):
        add_us()
        response = self.apply(consultation_category='general', consultation_fee=10, country_code='us')
        self.assertEqual((response.status_code, response.data['currency']), (201, 'USD'))
        self.assertIn('$10', str(self.apply(consultation_category='general', consultation_fee=200, country_code='US').data))
        self.assertEqual(self.apply(consultation_category='specialist', consultation_fee=55, country_code='US').status_code, 201)
        self.assertEqual(self.apply(consultation_category='specialist', consultation_fee=57, country_code='US').status_code, 400)
        self.assertEqual(self.apply(consultation_category='general', consultation_fee=10, country_code='BR').status_code, 400)
