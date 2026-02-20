from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('results', '0007_result_proposed_themes'),
        ('interview', '0006_rename_interview_to_topic'),
    ]

    operations = [
        migrations.RenameField(
            model_name='result',
            old_name='interview',
            new_name='topic',
        ),
    ]
