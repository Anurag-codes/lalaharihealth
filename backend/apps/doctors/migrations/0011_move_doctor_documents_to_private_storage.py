"""Move doctor verification documents uploaded before 0010 from public media into private storage."""
import logging

from django.core.files.storage import FileSystemStorage
from django.db import migrations

logger = logging.getLogger(__name__)


def move_documents_to_private_storage(apps, schema_editor):
    from apps.core.storage import private_document_storage

    public, private = FileSystemStorage(), private_document_storage()
    DoctorDocument = apps.get_model('doctors', 'DoctorDocument')
    for name in DoctorDocument.objects.exclude(file='').values_list('file', flat=True).distinct().iterator():
        if not public.exists(name):
            continue
        if not private.exists(name):
            with public.open(name, 'rb') as handle:
                saved = private.save(name, handle)
            if saved != name:
                logger.error('Could not move doctor document %s to private storage; the public copy was kept.', name)
                continue
        if private.size(name) != public.size(name):
            logger.error('Private copy of doctor document %s differs; the public copy was kept.', name)
            continue
        public.delete(name)


class Migration(migrations.Migration):

    dependencies = [
        ('doctors', '0010_alter_doctordocument_options_and_more'),
    ]

    operations = [
        migrations.RunPython(move_documents_to_private_storage, migrations.RunPython.noop),
    ]
