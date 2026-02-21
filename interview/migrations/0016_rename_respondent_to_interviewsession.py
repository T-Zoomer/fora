from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('interview', '0015_remove_respondent_is_complete'),
    ]

    operations = [
        migrations.RenameModel('Respondent', 'InterviewSession'),
        migrations.AlterField(
            model_name='interviewsession',
            name='interview',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sessions',
                to='interview.interview',
            ),
        ),
        migrations.RenameField(
            model_name='answer',
            old_name='respondent',
            new_name='session',
        ),
        migrations.AlterUniqueTogether(
            name='answer',
            unique_together={('topic', 'session')},
        ),
        migrations.AlterField(
            model_name='topic',
            name='name',
            field=models.CharField(max_length=500),
        ),
    ]
