import json

from django.conf import settings
from openai import OpenAI

from questions.models import Answer


def run_thematic_coding(interview):
    """
    Analyze answers using GPT-4o to identify themes/codes.
    Returns a list of themes with their descriptions and associated answer IDs.
    """
    answers = list(Answer.objects.filter(interview=interview).values('id', 'text'))

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
Analyze the provided interview answers and identify the main themes/codes present.

IMPORTANT GUIDELINES:
1. Focus on the WHY - themes should capture underlying causes, factors, and drivers
2. Theme names should be specific and actionable (e.g., "Meeting overload", "Remote work flexibility", "Manager support", "Unclear priorities")
3. DO NOT create sentiment-based themes like "Positive feelings", "Negative experiences", "Satisfied employees" - sentiment is already captured separately
4. An answer can and SHOULD belong to multiple themes when it mentions multiple factors
5. MAXIMUM 9 THEMES - prioritize the most significant and frequently mentioned factors
6. Each theme must have at least 2 answers - do not create themes for one-off mentions

For each theme, provide:
1. A short descriptive name (2-5 words) that explains WHAT is affecting people
2. A description (1-2 sentences) explaining the theme
3. The IDs of ALL answers that mention this factor

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
                "content": f"Analyze these interview answers and identify themes based on the underlying factors and causes mentioned:\n\n{answers_text}"
            }
        ],
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    themes = result.get("themes", [])

    # Filter themes with at least 2 answers and limit to 9
    themes = [t for t in themes if len(t.get("answer_ids", [])) >= 2]
    themes = themes[:9]

    return themes


def run_sentiment_analysis(interview):
    """
    Analyze the sentiment of each answer using GPT-4o.
    Returns a dict with average score and per-answer scores.
    Scores range from 1 (very negative) to 10 (very positive).
    """
    answers = list(Answer.objects.filter(interview=interview).values('id', 'text'))

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
            },
            {
                "role": "user",
                "content": f"Score the sentiment of these interview answers:\n\n{answers_text}"
            }
        ],
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    answer_scores = result.get("answers", [])

    # Calculate average
    if answer_scores:
        avg = sum(a["score"] for a in answer_scores) / len(answer_scores)
        avg = round(avg, 1)
    else:
        avg = None

    return {
        "average": avg,
        "answers": answer_scores
    }


def generate_summary(interview):
    """
    Generate an AI summary of all answers to an interview.
    Returns a concise paragraph summarizing the key points.
    """
    answers = list(Answer.objects.filter(interview=interview).values('id', 'text'))

    if not answers:
        return ""

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    answers_text = "\n".join([f"- {a['text']}" for a in answers])

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """You are an expert at summarizing survey responses.
Write a concise summary (2-4 sentences) that captures the main points and overall sentiment of the responses.
Focus on the most common themes and any notable patterns or outliers.
Write in a neutral, professional tone. Do not use bullet points."""
            },
            {
                "role": "user",
                "content": f"Summarize these responses to the interview \"{interview.text}\":\n\n{answers_text}"
            }
        ],
        max_tokens=300
    )

    return response.choices[0].message.content


def chat_with_all_answers(user_message, chat_history=None):
    """
    Chat about all interview answers using GPT-4o.
    The AI has access to all interviews and their answers.
    """
    from questions.models import Interview

    interviews = Interview.objects.all().order_by('order')

    # Build context with all interviews and answers
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

Based on this data, answer the user's questions. You can:
- Summarize findings across all questions
- Identify patterns and correlations
- Provide specific examples from responses
- Suggest actionable insights for improving productivity
- Compare responses across different questions

Be specific and reference actual responses when relevant. Be concise but comprehensive."""
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
