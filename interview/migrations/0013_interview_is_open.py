from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interview', '0012_interview_uuid'),
    ]

    operations = [
        migrations.AddField(
            model_name='interview',
            name='is_open',
            field=models.BooleanField(default=True),
        ),
    ]
