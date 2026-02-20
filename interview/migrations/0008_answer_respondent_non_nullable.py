from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('interview', '0007_rename_app_tables'),
    ]

    operations = [
        migrations.AlterField(
            model_name='answer',
            name='respondent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='interview.respondent'),
        ),
    ]
