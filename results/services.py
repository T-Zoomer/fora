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
    Chat about all interview answers using GPT-4o with tool calling.
    The AI has access to all interviews, their answers, and analysis tools.
    """
    from questions.models import Interview
    from results.tools import CHAT_TOOLS, execute_tool

    interviews = Interview.objects.all().order_by('order')

    # Build context with all interviews and answers
    context_parts = []
    topic_list = []
    total_answers = 0

    for interview in interviews:
        answers = list(Answer.objects.filter(interview=interview).values('text'))
        if answers:
            answers_text = "\n".join([f"  - {a['text']}" for a in answers])
            context_parts.append(f"**{interview.text}** (ID: {interview.id}, {len(answers)} responses):\n{answers_text}")
            topic_list.append(f"- ID {interview.id}: {interview.text}")
            total_answers += len(answers)

    if total_answers == 0:
        return "There are no interview responses yet."

    full_context = "\n\n".join(context_parts)
    topics_reference = "\n".join(topic_list)

    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    messages = [
        {
            "role": "system",
            "content": f"""You are a helpful assistant that analyzes survey responses about workplace productivity and wellbeing.

AVAILABLE INTERVIEW TOPICS:
{topics_reference}

Here is the complete survey data:

{full_context}

You have access to analysis tools that can compute statistics and correlations. Use these tools when the user asks about:
- Sentiment scores, averages, or comparisons between topics
- Theme analysis or what themes are present
- Correlations between topics or between themes and sentiment
- What factors are driving positive or negative sentiment

When using tools, always use the topic IDs listed above. After receiving tool results, synthesize the data into a clear, helpful response.

Be specific and reference actual responses when relevant. Be concise but comprehensive."""
        }
    ]

    if chat_history:
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

    # Tool calling loop (max 5 iterations)
    max_iterations = 5
    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=CHAT_TOOLS,
            max_tokens=1000
        )

        response_message = response.choices[0].message

        # If no tool calls, return the final response
        if not response_message.tool_calls:
            return response_message.content

        # Add assistant message with tool calls
        messages.append(response_message)

        # Execute each tool call and add results
        for tool_call in response_message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments

            # Execute the tool
            tool_result = execute_tool(tool_name, tool_args)

            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_result
            })

    # If we hit max iterations, get a final response without tools
    final_response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=1000
    )

    return final_response.choices[0].message.content
