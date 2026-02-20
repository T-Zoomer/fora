from django.core.management.base import BaseCommand

from interview.models import Answer, Topic, Respondent

MAIN_QUESTION = "How productive were you feeling at work this week?"
FOLLOWUP_QUESTION = "What was making you feel productive (or not productive) this week?"

# 50 pairs of (main answer, follow-up answer)
RESPONSES = [
    (
        "Honestly not very productive. I felt like I was just going through the motions most days.",
        "We had back-to-back meetings almost every day. By the time I actually got to sit down and work, I was already mentally exhausted.",
    ),
    (
        "Pretty productive overall! Got a lot done and felt good at the end of each day.",
        "I blocked off my mornings for deep work and kept my inbox closed. That made a huge difference.",
    ),
    (
        "Mixed bag. Some days were great, others I couldn't focus at all.",
        "The open office is really hard when colleagues are having loud conversations. On quiet days I flew through my tasks.",
    ),
    (
        "Very productive. One of my better weeks in a while.",
        "I had a clear list of priorities and no unexpected fires to put out. I just worked through the list.",
    ),
    (
        "Not productive at all. I'm burnt out and it's showing.",
        "I've been doing overtime for three weeks now and I'm running on empty. I can't concentrate for more than twenty minutes.",
    ),
    (
        "Fairly productive. Got most of what I planned done.",
        "My manager was away so there were fewer check-ins and I could just get on with things.",
    ),
    (
        "Below average week for me. Too many interruptions.",
        "Slack notifications were constant. Every time I got into something someone would ping me.",
    ),
    (
        "Really productive! I surprised myself with how much I shipped.",
        "I started using the Pomodoro technique again. Twenty-five minutes of focus, five minute break. It really works for me.",
    ),
    (
        "Moderately productive. Could have been better.",
        "I spent too much time in meetings that could have been emails. At least three of them had nothing to do with my work.",
    ),
    (
        "Very unproductive. I was dealing with a personal situation and couldn't focus.",
        "Family stuff at home made it hard to switch off mentally. Working from home made the boundary even blurrier.",
    ),
    (
        "Productive week. Crossed off most of my to-do list.",
        "The deadline at the end of the week gave me a natural sense of urgency. I work well under a bit of pressure.",
    ),
    (
        "Not very productive. System issues kept slowing me down.",
        "Our internal tools were slow and crashing all week. I lost hours waiting for things to load or re-doing work after crashes.",
    ),
    (
        "Above average. I felt in flow for most of it.",
        "I found a good rhythm early Monday and it carried through. Good sleep probably helped too.",
    ),
    (
        "Quite unproductive. A lot of waiting around for others.",
        "I was blocked on a task because another team hadn't delivered their part yet. I couldn't move forward.",
    ),
    (
        "Pretty good week overall. Felt energized and focused.",
        "I went for a run every morning before logging on. The exercise really sets me up well for the day.",
    ),
    (
        "Average. Some wins, some wasted time.",
        "The daily standups run way too long. What should be fifteen minutes turns into an hour.",
    ),
    (
        "Not productive. Too much context switching.",
        "I was juggling four different projects and kept having to switch gears. Never got deep into anything.",
    ),
    (
        "Very productive. Best week in a long time.",
        "We finished a big phase of the project and everything clicked. The team was aligned and I knew exactly what to do.",
    ),
    (
        "Somewhat productive. Made progress but slowly.",
        "I was learning a new tool this week so everything took longer than usual. Not unproductive, just slow.",
    ),
    (
        "Unproductive. Felt stuck and uninspired.",
        "I'm not sure my work is going anywhere meaningful. That makes it hard to motivate myself.",
    ),
    (
        "Really good week. Hit all my targets.",
        "I came in with a clear plan on Monday and stuck to it. Preparation made all the difference.",
    ),
    (
        "Not great. Too many ad-hoc requests came in.",
        "People kept pinging me with urgent things that turned out not to be urgent. Hard to stay on track.",
    ),
    (
        "Productive in the mornings, not at all in the afternoons.",
        "After lunch I always hit a wall. I think I need to restructure my day so the hard work happens in the morning.",
    ),
    (
        "Very unproductive. I was sick for two days.",
        "I had a cold and tried to push through, which was a mistake. I barely produced anything and felt awful.",
    ),
    (
        "Good week. I feel like I added real value.",
        "I got to lead a workshop that went really well. That kind of meaningful work makes me feel productive.",
    ),
    (
        "Mediocre. I was technically busy but not productive.",
        "Lots of emails and administrative tasks. Busy-work rather than actual progress.",
    ),
    (
        "Quite productive. Wrapped up a project I'd been dragging.",
        "Finally getting that project off my plate freed up so much mental energy. I felt lighter all week.",
    ),
    (
        "Poor week. Lots of uncertainty about a reorg.",
        "There are rumours about restructuring and nobody knows what's happening. It's hard to focus when the future is unclear.",
    ),
    (
        "Very productive! I hit flow state multiple times.",
        "I wore headphones with instrumental music and it completely shut out distractions. I need to do this more.",
    ),
    (
        "Not productive. Onboarding a new team member took most of my time.",
        "I spent a lot of time supporting the new joiner which I'm happy to do, but it meant my own work piled up.",
    ),
    (
        "Solid week. I'm pleased with what I accomplished.",
        "My to-do list was realistic for once. I didn't overcommit and actually finished everything I set out to do.",
    ),
    (
        "Below par. I struggled with low energy all week.",
        "I haven't been sleeping well. When I'm tired everything takes twice as long and I make more mistakes.",
    ),
    (
        "Productive despite a busy week with many meetings.",
        "I got better at saying no to optional meetings. Protecting two hours a day of focus time helped a lot.",
    ),
    (
        "Not very productive. Working remotely felt isolating this week.",
        "I missed the energy of the office. When I'm alone at home it's too quiet and I lose motivation.",
    ),
    (
        "Highly productive. I was in the zone.",
        "The project is at an exciting stage and I'm genuinely interested in the problem. Intrinsic motivation is powerful.",
    ),
    (
        "Average week. Nothing special.",
        "Business as usual. No big blockers but no exciting momentum either. Just steady work.",
    ),
    (
        "Not productive. Unclear requirements kept me going in circles.",
        "I kept starting things and then realising I didn't have enough information. I should have clarified upfront.",
    ),
    (
        "Productive! I managed to work on a passion project too.",
        "We have 10% time for personal projects and I actually used it this week. That made me feel more productive overall.",
    ),
    (
        "Very poor week. Personal admin took over.",
        "Had to deal with a lot of personal admin — bank, insurance, appointments — and it bled into work time.",
    ),
    (
        "Good week. Team collaboration was really effective.",
        "We had a great pairing session with a colleague and solved something that had been blocked for days. Energy was high.",
    ),
    (
        "Not productive. My laptop had issues all week.",
        "Slow machine, constant updates, had to restart multiple times a day. It sounds trivial but it really kills momentum.",
    ),
    (
        "Pretty productive. Got ahead of next week too.",
        "I had a light agenda so I used the time to get ahead. Feels great to go into Monday not stressed.",
    ),
    (
        "Somewhat unproductive. Hard to prioritise.",
        "Everything felt urgent and I wasn't sure what to tackle first. I need a better system for prioritisation.",
    ),
    (
        "Very productive. Clear goals made all the difference.",
        "My manager set very specific goals at the start of the week. Knowing exactly what success looks like helps me work faster.",
    ),
    (
        "Not great. Long commute days drained me.",
        "I had to go into the office three days this week. The commute is ninety minutes each way and by the time I get home I'm done.",
    ),
    (
        "Productive and motivated. Really enjoyed this week.",
        "Got positive feedback on work I did last month. Recognition gives me a real boost.",
    ),
    (
        "Mediocre week. Too many small tasks, no big wins.",
        "I cleared a lot of tiny tickets but didn't make progress on the meaningful stuff. Felt like running on a treadmill.",
    ),
    (
        "Quite productive. Focused environment helped.",
        "I worked from a quiet café for two days instead of home. The change of scenery did wonders for my concentration.",
    ),
    (
        "Not productive at all. Team conflict was draining.",
        "There was tension between two colleagues this week and it affected the whole team. Hard to focus when the atmosphere is off.",
    ),
    (
        "Good week. I finished strong.",
        "Thursday and Friday were my best days. I think I warm up during the week and hit my stride towards the end.",
    ),
]


class Command(BaseCommand):
    help = "Seed 50 fake productivity responses for two interview questions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without writing to the database",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(f"Would create Topic: '{MAIN_QUESTION}'")
            self.stdout.write(f"Would create Topic: '{FOLLOWUP_QUESTION}'")
            self.stdout.write(f"Would create {len(RESPONSES)} respondents with answers for each question.")
            for i, (main, followup) in enumerate(RESPONSES[:3], 1):
                self.stdout.write(f"\n  Respondent {i}:")
                self.stdout.write(f"    Q1: {main[:80]}")
                self.stdout.write(f"    Q2: {followup[:80]}")
            self.stdout.write("  ...")
            return

        main_topic, created = Topic.objects.get_or_create(text=MAIN_QUESTION)
        self.stdout.write(
            f"{'Created' if created else 'Using existing'} Topic (id={main_topic.pk}): {MAIN_QUESTION}"
        )

        followup_topic, created = Topic.objects.get_or_create(text=FOLLOWUP_QUESTION)
        self.stdout.write(
            f"{'Created' if created else 'Using existing'} Topic (id={followup_topic.pk}): {FOLLOWUP_QUESTION}"
        )

        for main_text, followup_text in RESPONSES:
            respondent = Respondent.objects.create()
            Answer.objects.create(topic=main_topic, respondent=respondent, text=main_text)
            Answer.objects.create(topic=followup_topic, respondent=respondent, text=followup_text)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(RESPONSES)} respondents, "
                f"{len(RESPONSES)} answers for '{MAIN_QUESTION}', "
                f"{len(RESPONSES)} answers for '{FOLLOWUP_QUESTION}'."
            )
        )
