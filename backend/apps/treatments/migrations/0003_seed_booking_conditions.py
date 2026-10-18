from django.db import migrations
from django.utils.text import slugify

# Starter list for the booking Symptoms dropdowns. Edit or extend in Django admin.
STARTER_CONDITIONS = [
    ('Headache', 'Specific Headache Type', [
        ('Migraine', ['With Aura', 'Without Aura', 'Chronic']),
        ('Tension-type Headache', ['Episodic', 'Chronic']),
        ('Cluster Headache', ['Episodic', 'Chronic']),
        ('Sinus Headache', ['Acute', 'Chronic']),
    ]),
    ('Fever', 'Specific Fever Type', [
        ('Viral Fever', []), ('Dengue', []), ('Typhoid', []), ('Malaria', []),
    ]),
    ('Diabetes', 'Specific Diabetes Type', [
        ('Type 1 Diabetes', []), ('Type 2 Diabetes', []), ('Gestational Diabetes', []), ('Prediabetes', []),
    ]),
    ('Thyroid', 'Specific Thyroid Condition', [
        ('Hypothyroidism', []), ('Hyperthyroidism', []),
    ]),
    ('High Blood Pressure', '', []),
    ('Cough & Cold', '', []),
    ('Stomach Problem', '', []),
    ('Skin Problem', '', []),
    ('Joint Pain', '', []),
]


def seed(apps, schema_editor):
    Condition = apps.get_model('treatments', 'Condition')
    ConditionType = apps.get_model('treatments', 'ConditionType')
    ConditionVariant = apps.get_model('treatments', 'ConditionVariant')
    for name, type_label, types in STARTER_CONDITIONS:
        condition = Condition.objects.filter(name__iexact=name).first()
        if condition is None:
            condition = Condition.objects.filter(slug=slugify(name)).first()
        if condition is None:
            condition = Condition.objects.create(name=name, slug=slugify(name), type_label=type_label)
        elif not condition.type_label and type_label:
            condition.type_label = type_label
            condition.save(update_fields=['type_label'])
        for type_order, (type_name, variants) in enumerate(types, start=1):
            condition_type, _ = ConditionType.objects.get_or_create(
                condition=condition, name=type_name, defaults={'display_order': type_order},
            )
            for variant_order, variant_name in enumerate(variants, start=1):
                ConditionVariant.objects.get_or_create(
                    condition_type=condition_type, name=variant_name, defaults={'display_order': variant_order},
                )


class Migration(migrations.Migration):

    dependencies = [
        ('treatments', '0002_condition_type_label_conditiontype_conditionvariant_and_more'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
