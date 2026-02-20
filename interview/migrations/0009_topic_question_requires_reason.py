from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interview', '0008_answer_respondent_non_nullable'),
    ]

    operations = [
        migrations.AddField(
            model_name='topic',
            name='question',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='topic',
            name='requires_reason',
            field=models.BooleanField(
                default=False,
                help_text='If true, the user must give both an assessment and a reason to mark this topic covered.',
            ),
        ),
    ]
