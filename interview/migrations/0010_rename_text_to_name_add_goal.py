from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interview', '0009_topic_question_requires_reason'),
    ]

    operations = [
        migrations.RenameField(
            model_name='topic',
            old_name='text',
            new_name='name',
        ),
        migrations.RemoveField(
            model_name='topic',
            name='question',
        ),
        migrations.RemoveField(
            model_name='topic',
            name='requires_reason',
        ),
        migrations.AddField(
            model_name='topic',
            name='goal',
            field=models.TextField(
                blank=True,
                default='',
                help_text=(
                    'What you want to find out from respondents. '
                    'Used to guide the interview questions and to judge whether the topic has been sufficiently covered.'
                ),
            ),
        ),
    ]
