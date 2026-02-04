import json

from django.conf import settings
from openai import OpenAI

from questions.models import Answer


def run_thematic_coding(question):
    """
    Analyze answers using GPT-4o to identify themes/codes.
    Returns a list of themes with their descriptions and associated answer IDs.
    """
    answers = list(Answer.objects.filter(question=question).values('id', 'text'))

    if not answers:
        return []

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Build the prompt with all answers
    answers_text = "\n".join([f"[ID: {a['id']}] {a['text']}" for a in answers])

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are an expert qualitative researcher skilled in thematic coding.
Analyze the provided survey answers and identify the main themes/codes present.
For each theme, provide:
1. A short name (2-5 words)
2. A description (1-2 sentences)
3. The IDs of answers that belong to this theme

An answer can belong to multiple themes. Be thorough but don't create redundant themes.

Respond in JSON format:
{
  "themes": [
    {
      "name": "Theme Name",
      "description": "Description of what this theme represents",
      "answer_ids": [1, 2, 3]
    }
  ]
}"""
            },
            {
                "role": "user",
                "content": f"Analyze these survey answers and identify themes:\n\n{answers_text}"
            }
        ],
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    return result.get("themes", [])


def run_sentiment_analysis(question):
    """
    Analyze the sentiment of each answer using GPT-4o.
    Returns a dict with average score and per-answer scores.
    Scores range from 0.0 (very negative) to 1.0 (very positive).
    """
    answers = list(Answer.objects.filter(question=question).values('id', 'text'))

    if not answers:
        return {"average": None, "answers": []}

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    answers_text = "\n".join([f"[ID: {a['id']}] {a['text']}" for a in answers])

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are an expert at sentiment analysis.
Score each answer from 0.0 to 1.0 based on emotional tone:
- 0.0 = very negative
- 0.5 = neutral
- 1.0 = very positive

Respond in JSON format:
{
  "answers": [
    {"id": 1, "score": 0.8},
    {"id": 2, "score": 0.3}
  ]
}

Include every answer ID provided. Be consistent in your scoring."""
            },
            {
                "role": "user",
                "content": f"Score the sentiment of these survey answers:\n\n{answers_text}"
            }
        ],
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    answer_scores = result.get("answers", [])

    # Calculate average
    if answer_scores:
        avg = sum(a["score"] for a in answer_scores) / len(answer_scores)
        avg = round(avg, 2)
    else:
        avg = None

    return {
        "average": avg,
        "answers": answer_scores
    }
