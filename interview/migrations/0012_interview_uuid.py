import uuid

from django.db import migrations, models


def populate_uuids(apps, schema_editor):
    Interview = apps.get_model('interview', 'Interview')
    for interview in Interview.objects.all():
        interview.uuid = uuid.uuid4()
        interview.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ('interview', '0011_interview_model'),
    ]

    operations = [
        # Step 1: add nullable (no unique yet)
        migrations.AddField(
            model_name='interview',
            name='uuid',
            field=models.UUIDField(null=True),
        ),
        # Step 2: populate existing rows
        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
        # Step 3: make non-nullable and unique
        migrations.AlterField(
            model_name='interview',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
    ]
