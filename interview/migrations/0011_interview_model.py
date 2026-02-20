from django.db import migrations, models
import django.db.models.deletion


def create_default_interview(apps, schema_editor):
    Interview = apps.get_model('interview', 'Interview')
    Topic = apps.get_model('interview', 'Topic')
    default_interview = Interview.objects.create(name='Default Interview')
    Topic.objects.all().update(interview=default_interview)


class Migration(migrations.Migration):

    dependencies = [
        ('interview', '0010_rename_text_to_name_add_goal'),
    ]

    operations = [
        # 1. Create the Interview table
        migrations.CreateModel(
            name='Interview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('intro_message', models.TextField(
                    blank=True,
                    default='',
                    help_text='Opening message shown to the respondent at the start of the interview.',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        # 2. Add nullable interview FK to Topic
        migrations.AddField(
            model_name='topic',
            name='interview',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='topics',
                to='interview.interview',
            ),
        ),
        # 3. Create Default Interview and assign all existing topics to it
        migrations.RunPython(create_default_interview, migrations.RunPython.noop),
        # 4. Make topic.interview non-nullable
        migrations.AlterField(
            model_name='topic',
            name='interview',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='topics',
                to='interview.interview',
            ),
        ),
        # 5. Add nullable interview FK to Respondent
        migrations.AddField(
            model_name='respondent',
            name='interview',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='respondents',
                to='interview.interview',
            ),
        ),
    ]
