from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0008_rename_interview_to_topic'),
    ]

    operations = [
        migrations.AlterField(
            model_name='result',
            name='analyzed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
