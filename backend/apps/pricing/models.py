from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

country_code_validator = RegexValidator(r'^[A-Z]{2}$', 'Use the 2-letter ISO country code in capitals, e.g. IN, US, AE.')
currency_validator = RegexValidator(r'^[A-Z]{3}$', 'Use the 3-letter ISO currency code in capitals, e.g. INR, USD, AED.')


class CountryPricing(models.Model):
    """General physician consultation price per country, plus the specialist fee range doctors can choose there.

    Amounts are whole units of the country's currency. The default row (India, INR 200) is used when the
    visitor's location is unknown or their country has no active row.
    """

    country_code = models.CharField(max_length=2, unique=True, validators=[country_code_validator])
    country_name = models.CharField(max_length=100)
    currency = models.CharField(max_length=3, validators=[currency_validator], help_text='ISO 4217 code, e.g. INR, USD')
    currency_symbol = models.CharField(max_length=8, help_text='Shown before amounts, e.g. ₹, $, £, AED')
    general_fee = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], help_text='General physician consultation fee charged to patients',
    )
    specialist_fee_min = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    specialist_fee_max = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    specialist_fee_step = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)], help_text='Specialist fees must be min + a multiple of this step',
    )
    is_default = models.BooleanField(
        default=False, help_text='Used when location is unknown or the country has no active pricing. Exactly one row.',
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', 'country_name']
        verbose_name = 'country pricing'
        verbose_name_plural = 'country pricing'
        constraints = [
            models.UniqueConstraint(fields=['is_default'], condition=models.Q(is_default=True), name='pricing_single_default'),
        ]

    def __str__(self):
        return f'{self.country_name} ({self.currency} {self.general_fee})'

    def clean(self):
        self.country_code = (self.country_code or '').upper()
        self.currency = (self.currency or '').upper()
        errors = {}
        if self.specialist_fee_min and self.specialist_fee_max and self.specialist_fee_min > self.specialist_fee_max:
            errors['specialist_fee_max'] = 'Must be at least the minimum specialist fee.'
        elif self.specialist_fee_step and (self.specialist_fee_max - self.specialist_fee_min) % self.specialist_fee_step:
            errors['specialist_fee_step'] = 'Maximum minus minimum must be a multiple of the step.'
        if self.is_default and not self.is_active:
            errors['is_active'] = 'The default pricing must stay active.'
        if errors:
            raise ValidationError(errors)
