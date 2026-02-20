from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('interview', '0006_rename_interview_to_topic'),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE questions_respondent RENAME TO interview_respondent;",
                "ALTER TABLE questions_topic RENAME TO interview_topic;",
                "ALTER TABLE questions_answer RENAME TO interview_answer;",
            ],
            reverse_sql=[
                "ALTER TABLE interview_respondent RENAME TO questions_respondent;",
                "ALTER TABLE interview_topic RENAME TO questions_topic;",
                "ALTER TABLE interview_answer RENAME TO questions_answer;",
            ],
        ),
    ]
