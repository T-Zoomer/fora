import csv

from django.core.management.base import BaseCommand

from questions.models import Answer, Interview, Respondent

QUESTION_TEXT = (
    "U heeft aangegeven dat regels over gezond en veilig werken en/of andere regels of wetten "
    "u veel tijd en/of moeite kosten. Om welke regels of wetten gaat het dan?"
)


class Command(BaseCommand):
    help = "Import question and answers from ZEA25U_RegAnders_geanonimiseerd.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            default="ZEA25U_RegAnders_geanonimiseerd.csv",
            help="Path to the CSV file (default: ZEA25U_RegAnders_geanonimiseerd.csv)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be imported without writing to the database",
        )

    def handle(self, *args, **options):
        csv_path = options["csv"]
        dry_run = options["dry_run"]

        with open(csv_path, encoding="latin-1") as f:
            rows = [row for row in csv.DictReader(f, delimiter=";") if row["RegAnders"].strip()]

        self.stdout.write(f"Found {len(rows)} non-empty answers in {csv_path}")

        if dry_run:
            self.stdout.write("Dry run — no changes written.")
            for row in rows[:5]:
                self.stdout.write(f"  {row['SteekproefEenheidID']}: {row['RegAnders'][:80]}")
            return

        interview, created = Interview.objects.get_or_create(text=QUESTION_TEXT)
        if created:
            self.stdout.write(f"Created Interview (id={interview.pk})")
        else:
            self.stdout.write(f"Using existing Interview (id={interview.pk})")

        imported = 0
        for row in rows:
            respondent = Respondent.objects.create()
            Answer.objects.create(
                interview=interview,
                respondent=respondent,
                text=row["RegAnders"].strip(),
            )
            imported += 1

        self.stdout.write(self.style.SUCCESS(f"Imported {imported} answers."))
