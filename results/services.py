import json

from django.conf import settings
from openai import OpenAI

from questions.models import Answer
from results.llm import generate


BATCH_SIZE = 50
MAX_THEMES = 12


def _discover_themes(answers, question_text):
    """
    Pass 1: Send ALL answers to discover themes. No sampling.
    Returns list of theme dicts: [{name, description, answer_ids: [], excerpts: {}}]
    """
    answers_text = "\n".join([f"[ID: {a['id']}] {a['text']}" for a in answers])

    system_prompt = f"""You are an expert qualitative researcher skilled in thematic coding.
Analyze the provided interview answers and identify the main themes present.

IMPORTANT GUIDELINES:
- Focus on the WHY — themes should capture underlying causes, factors, and drivers
- Theme names should be specific and actionable (e.g. "Meeting overload", "Remote work flexibility", "Unclear priorities")
- DO NOT create sentiment-based themes like "Positive feelings" or "Negative experiences" — sentiment is captured separately
- Maximum {MAX_THEMES} themes — prioritise the most significant and frequently mentioned factors
- Each theme must apply to at least 2 answers
- Return only theme names and descriptions — no answer assignments needed at this stage

Respond in JSON format:
{{
  "themes": [
    {{
      "name": "Theme Name",
      "description": "Description of what this theme represents"
    }}
  ]
}}"""

    user_prompt = f"Analyze these interview answers for the question \"{question_text}\" and identify the main underlying themes:\n\n{answers_text}"

    raw = json.loads(generate(system_prompt, user_prompt, json_mode=True))
    themes = raw.get("themes", [])
    print(f"  [themes] discovered {len(themes)} themes: {[t['name'] for t in themes]}")
    return [{"name": t["name"], "description": t["description"], "answer_ids": [], "excerpts": {}} for t in themes]


def _classify_answers(answers, themes):
    """
    Pass 2: Classify all answers into discovered themes in batches of BATCH_SIZE.
    Modifies themes in-place: appends to answer_ids and fills excerpts dict.
    """
    if not themes:
        return

    theme_ref = "\n".join([
        f"{i + 1}. {t['name']}: {t['description']}"
        for i, t in enumerate(themes)
    ])

    system_prompt = f"""You are a qualitative research assistant performing thematic coding.

THEMES:
{theme_ref}

For each answer, identify which theme numbers apply (can be multiple, or empty list if none fit).
For each matched theme, extract a short verbatim excerpt from the answer that relates to it.

Respond in JSON format:
{{
  "assignments": [
    {{
      "id": <answer_id as integer>,
      "themes": [
        {{"number": <theme_number>, "excerpt": "<verbatim phrase from the answer>"}}
      ]
    }}
  ]
}}

Include every answer ID in the response even if it matches no themes (use empty themes list).
Use only theme numbers 1 to {len(themes)}."""

    total_batches = (len(answers) + BATCH_SIZE - 1) // BATCH_SIZE
    for batch_start in range(0, len(answers), BATCH_SIZE):
        batch = answers[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        print(f"  [classify] batch {batch_num}/{total_batches} ({len(batch)} answers)...")

        answers_text = "\n".join([f"[ID: {a['id']}] {a['text']}" for a in batch])
        result = json.loads(generate(system_prompt, f"Classify these answers:\n\n{answers_text}", json_mode=True))

        assigned_in_batch = sum(1 for a in result.get("assignments", []) if a.get("themes"))
        print(f"  [classify] batch {batch_num}/{total_batches} done — {assigned_in_batch}/{len(batch)} answers matched a theme")

        for assignment in result.get("assignments", []):
            answer_id = assignment.get("id")
            for match in assignment.get("themes", []):
                theme_num = match.get("number")
                excerpt = match.get("excerpt", "")
                if theme_num and 1 <= theme_num <= len(themes):
                    theme = themes[theme_num - 1]
                    if answer_id not in theme["answer_ids"]:
                        theme["answer_ids"].append(answer_id)
                    theme["excerpts"][str(answer_id)] = excerpt


def run_thematic_coding(interview):
    """
    Two-pass thematic coding:
    - Pass 1: discover themes from ALL answers (no sampling)
    - Pass 2: classify all answers in batches of BATCH_SIZE
    Returns a list of themes with answer_ids and excerpts. Unassigned answers go to "Other".
    """
    answers = list(Answer.objects.filter(interview=interview).values('id', 'text'))

    if not answers:
        return []

    print(f"\n[thematic coding] '{interview.text}' — {len(answers)} answers")

    print(f"[pass 1] discovering themes from all {len(answers)} answers...")
    themes = _discover_themes(answers, interview.text)

    if not themes:
        print("[pass 1] no themes found, aborting")
        return []

    total_batches = (len(answers) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"[pass 2] classifying {len(answers)} answers in {total_batches} batches of {BATCH_SIZE}...")
    _classify_answers(answers, themes)

    # Filter themes with fewer than 2 answers and cap at MAX_THEMES
    before = len(themes)
    themes = [t for t in themes if len(t["answer_ids"]) >= 2]
    themes = themes[:MAX_THEMES]
    print(f"  [filter] kept {len(themes)}/{before} themes (≥2 answers, max {MAX_THEMES})")

    # Collect all assigned answer IDs
    assigned_ids = set()
    for theme in themes:
        assigned_ids.update(theme["answer_ids"])

    # Put unassigned answers in an "Other" theme
    unassigned = [a for a in answers if a['id'] not in assigned_ids]
    if unassigned:
        print(f"  [other] {len(unassigned)} answers unassigned → adding 'Other' theme")
        themes.append({
            "name": "Other",
            "description": "Answers that did not clearly fit into any of the identified themes.",
            "answer_ids": [a['id'] for a in unassigned],
            "excerpts": {},
        })

    print(f"  [done] {len(themes)} final themes, {len(assigned_ids)} answers assigned to named themes\n")
    return themes


def run_sentiment_analysis(interview):
    """
    Analyze the sentiment of each answer.
    Returns a dict with average score and per-answer scores (1-10).
    """
    answers = list(Answer.objects.filter(interview=interview).values('id', 'text'))

    if not answers:
        return {"average": None, "answers": []}

    answers_text = "\n".join([f"[ID: {a['id']}] {a['text']}" for a in answers])

    system_prompt = """You are an expert at sentiment analysis.
Score each answer from 1 to 10 based on emotional tone:
- 1 = very negative
- 5 = neutral
- 10 = very positive

Respond in JSON format:
{
  "answers": [
    {"id": 1, "score": 8},
    {"id": 2, "score": 3}
  ]
}

Include every answer ID provided. Be consistent in your scoring."""

    result = json.loads(generate(system_prompt, f"Score the sentiment of these interview answers:\n\n{answers_text}", json_mode=True))
    answer_scores = result.get("answers", [])

    avg = round(sum(a["score"] for a in answer_scores) / len(answer_scores), 1) if answer_scores else None

    return {"average": avg, "answers": answer_scores}


def generate_summary(interview):
    """
    Generate an AI summary of all answers to an interview.
    Returns a concise paragraph summarizing the key points.
    """
    answers = list(Answer.objects.filter(interview=interview).values('id', 'text'))

    if not answers:
        return ""

    answers_text = "\n".join([f"- {a['text']}" for a in answers])

    system_prompt = """You are an expert at summarizing survey responses.
Write a concise summary (2-4 sentences) that captures the main points and overall sentiment of the responses.
Focus on the most common themes and any notable patterns or outliers.
Write in a neutral, professional tone. Do not use bullet points."""

    return generate(system_prompt, f"Summarize these responses to the interview \"{interview.text}\":\n\n{answers_text}")


def chat_with_all_answers(user_message, chat_history=None):
    """
    Chat about all interview answers using GPT-4o.
    The AI has access to all interviews and their answers as context.
    """
    from questions.models import Interview

    interviews = Interview.objects.all().order_by('order')

    context_parts = []
    total_answers = 0

    for interview in interviews:
        answers = list(Answer.objects.filter(interview=interview).values('text'))
        if answers:
            answers_text = "\n".join([f"  - {a['text']}" for a in answers])
            context_parts.append(f"**{interview.text}** ({len(answers)} responses):\n{answers_text}")
            total_answers += len(answers)

    if total_answers == 0:
        return "There are no interview responses yet."

    full_context = "\n\n".join(context_parts)

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    messages = [
        {
            "role": "system",
            "content": f"""You are a helpful assistant that analyzes survey responses about workplace productivity and wellbeing.

Here is the complete survey data:

{full_context}

Answer questions based on the responses above. Be specific and reference actual responses when relevant. Be concise but comprehensive."""
        }
    ]

    if chat_history:
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=1000
    )

    return response.choices[0].message.content
