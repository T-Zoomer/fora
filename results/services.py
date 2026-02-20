import json

from interview.models import Answer, Topic
from results.llm import generate


BATCH_SIZE = 50
MAX_THEMES = 12


def _discover_themes(answers, question_text, custom_prompt=None):
    """
    Pass 1: Send ALL answers to discover themes. No sampling.
    Returns list of theme dicts: [{name, description, answer_ids: [], excerpts: {}}]
    """
    answers_text = "\n".join([f"[ID: {a['id']}] {a['text']}" for a in answers])

    custom_instructions = f"\nADDITIONAL INSTRUCTIONS FROM RESEARCHER:\n{custom_prompt.strip()}" if custom_prompt and custom_prompt.strip() else ""

    system_prompt = f"""You are an expert qualitative researcher skilled in thematic coding.
Analyze the provided interview answers and identify the main themes present.

IMPORTANT GUIDELINES:
- Focus on the WHY — themes should capture underlying causes, factors, and drivers
- Theme names should be specific and actionable (e.g. "Meeting overload", "Remote work flexibility", "Unclear priorities")
- DO NOT create sentiment-based themes like "Positive feelings" or "Negative experiences" — sentiment is captured separately
- Maximum {MAX_THEMES} themes — prioritise the most significant and frequently mentioned factors
- Each theme must apply to at least 2 answers
- Return only theme names and descriptions — no answer assignments needed at this stage{custom_instructions}

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


def discover_themes_only(topic, custom_prompt=None):
    """
    Pass 1 only: discover themes from all answers.
    Returns [{name, description}] — no answer assignments.
    """
    answers = list(Answer.objects.filter(topic=topic).values('id', 'text'))
    if not answers:
        return []
    print(f"\n[discover themes] '{topic.name}' — {len(answers)} answers")
    themes = _discover_themes(answers, topic.name, custom_prompt=custom_prompt)
    return [{"name": t["name"], "description": t["description"]} for t in themes]


def run_classification_with_themes(topic, themes):
    """
    Pass 2 only: classify answers against the provided themes.
    themes: [{name, description}] (user-edited list)
    Returns full themes with answer_ids and excerpts.
    """
    answers = list(Answer.objects.filter(topic=topic).values('id', 'text'))
    if not answers or not themes:
        return []

    # Build theme dicts with empty answer_ids/excerpts for classification
    full_themes = [
        {"name": t["name"], "description": t["description"], "answer_ids": [], "excerpts": {}}
        for t in themes
    ]

    total_batches = (len(answers) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"\n[classify with themes] '{topic.name}' — {len(answers)} answers, {len(full_themes)} themes, {total_batches} batches")
    _classify_answers(answers, full_themes)

    # Filter themes with no answers and cap at MAX_THEMES
    before = len(full_themes)
    full_themes = [t for t in full_themes if len(t["answer_ids"]) >= 1]
    full_themes = full_themes[:MAX_THEMES]
    print(f"  [filter] kept {len(full_themes)}/{before} themes (≥1 answer, max {MAX_THEMES})")

    # Collect all assigned answer IDs
    assigned_ids = set()
    for theme in full_themes:
        assigned_ids.update(theme["answer_ids"])

    # Put unassigned answers in an "Other" theme
    unassigned = [a for a in answers if a['id'] not in assigned_ids]
    if unassigned:
        print(f"  [other] {len(unassigned)} answers unassigned → adding 'Other' theme")
        full_themes.append({
            "name": "Other",
            "description": "Answers that did not clearly fit into any of the identified themes.",
            "answer_ids": [a['id'] for a in unassigned],
            "excerpts": {},
        })

    print(f"  [done] {len(full_themes)} final themes\n")
    return full_themes



def run_sentiment_analysis(topic):
    """
    Analyze the sentiment of each answer.
    Returns a dict with average score and per-answer scores (1-10).
    """
    answers = list(Answer.objects.filter(topic=topic).values('id', 'text'))

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


def generate_summary(topic):
    """
    Generate an AI summary of all answers to a topic.
    Returns a concise paragraph summarizing the key points.
    """
    answers = list(Answer.objects.filter(topic=topic).values('id', 'text'))

    if not answers:
        return ""

    answers_text = "\n".join([f"- {a['text']}" for a in answers])

    system_prompt = """You are an expert at summarizing survey responses.
Write a concise summary (2-4 sentences) that captures the main points and overall sentiment of the responses.
Focus on the most common themes and any notable patterns or outliers.
Write in a neutral, professional tone. Do not use bullet points."""

    return generate(system_prompt, f"Summarize these responses to the question \"{topic.name}\":\n\n{answers_text}")


def chat_with_all_answers(user_message, chat_history=None, interview=None):
    """
    Chat about all interview answers using GPT-4o.
    The AI has access to all interviews and their answers as context.
    """
    if interview is not None:
        topics = Topic.objects.filter(interview=interview).order_by('order')
    else:
        topics = Topic.objects.all().order_by('order')

    context_parts = []
    total_answers = 0

    for topic in topics:
        answers = list(Answer.objects.filter(topic=topic).values('text'))
        if answers:
            answers_text = "\n".join([f"  - {a['text']}" for a in answers])
            context_parts.append(f"**{topic.name}** ({len(answers)} responses):\n{answers_text}")
            total_answers += len(answers)

    if total_answers == 0:
        return "There are no interview responses yet."

    full_context = "\n\n".join(context_parts)

    system_prompt = f"""You are a helpful assistant that analyzes survey responses.

Here is the complete survey data:

{full_context}

Answer questions based on the responses above. Be specific and reference actual responses when relevant. Be concise but comprehensive."""

    return generate(system_prompt, user_message, history=chat_history)
