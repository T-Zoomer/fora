from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('interview', '0005_remove_respondent_uuid'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Interview',
            new_name='Topic',
        ),
        migrations.RenameField(
            model_name='answer',
            old_name='interview',
            new_name='topic',
        ),
    ]
