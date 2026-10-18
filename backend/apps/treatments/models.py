from django.db import models


class TreatmentSystem(models.TextChoices):
    """The medicine systems patients can compare for any given condition."""

    ALLOPATHY = 'allopathy', 'Allopathic'
    HOMEOPATHY = 'homeopathy', 'Homeopathic'
    AYURVEDA = 'ayurveda', 'Ayurvedic'
    UNANI = 'unani', 'Unani'
    HOME_REMEDY = 'home_remedy', 'Home Remedy'


class Condition(models.Model):
    """A symptom/disease that a patient can seek consultation for, e.g. Migraine."""

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True)
    description = models.TextField(blank=True)
    type_label = models.CharField(
        max_length=150, blank=True,
        help_text='Label of the second dropdown in the app, e.g. "Specific Headache Type".',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ConditionType(models.Model):
    """Second booking dropdown, e.g. Headache -> Cluster Headache."""

    condition = models.ForeignKey(Condition, related_name='types', on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['condition', 'display_order', 'name']
        constraints = [models.UniqueConstraint(fields=['condition', 'name'], name='unique_condition_type_name')]

    def __str__(self):
        return f'{self.condition.name} - {self.name}'


class ConditionVariant(models.Model):
    """Third booking dropdown, e.g. Cluster Headache -> Chronic."""

    condition_type = models.ForeignKey(ConditionType, related_name='variants', on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['condition_type', 'display_order', 'name']
        constraints = [models.UniqueConstraint(fields=['condition_type', 'name'], name='unique_condition_variant_name')]

    def __str__(self):
        return f'{self.condition_type} - {self.name}'


class TreatmentOption(models.Model):
    """How a specific condition can be treated under one medicine system."""

    condition = models.ForeignKey(Condition, related_name='treatment_options', on_delete=models.CASCADE)
    system = models.CharField(max_length=20, choices=TreatmentSystem.choices)
    summary = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    estimated_cost_min = models.PositiveIntegerField(help_text='Approx. minimum cost in INR')
    estimated_cost_max = models.PositiveIntegerField(help_text='Approx. maximum cost in INR')
    is_recommended = models.BooleanField(default=False, help_text='Doctor-recommended default option')

    class Meta:
        ordering = ['condition', 'system']

    def __str__(self):
        return f'{self.condition.name} - {self.get_system_display()}'
