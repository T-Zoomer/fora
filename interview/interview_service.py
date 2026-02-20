import json

from results.llm import generate


def analyze_message(user_message, chat_history, topics):
    """
    AI 1: Analyzer - Determines which topics have been sufficiently covered.

    For each topic, uses its goal to judge whether the respondent has addressed
    what we want to find out. Returns JSON keyed by str(topic.pk).
    """
    topic_lines = []
    schema_parts = []
    for topic in topics:
        goal_text = topic.goal if topic.goal else "Any substantive response on this topic."
        topic_lines.append(f'- ID {topic.pk}: "{topic.name}". Goal: {goal_text}')
        schema_parts.append(f'  "{topic.pk}": {{"covered": true/false, "text": "user\'s relevant words or null"}}')

    conversation_context = ""
    for msg in chat_history:
        role = "Interviewer" if msg["role"] == "assistant" else "User"
        conversation_context += f"{role}: {msg['content']}\n"
    conversation_context += f"User: {user_message}"

    system_prompt = """You analyze interview conversations to determine which topics have been sufficiently covered.

TOPICS:
{topics}

RULES:
- Evaluate the ENTIRE conversation, not just the latest message
- A topic is covered when the respondent has sufficiently addressed the stated goal
- If the user mentions a topic but hasn't addressed the goal fully, mark it not covered
- Extract the user's relevant words verbatim (or close paraphrase) as "text"

Respond with ONLY valid JSON:
{{{schema}}}""".format(
        topics="\n".join(topic_lines),
        schema="\n".join(schema_parts),
    )

    raw = generate(system_prompt, f"Analyze this conversation:\n\n{conversation_context}", json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {str(t.pk): {"covered": False, "text": None} for t in topics}


def generate_response(chat_history, user_message, topics, covered_topic_ids):
    """
    AI 2: Interviewer - Generates a conversational follow-up.

    Knows which topics remain and their goals, so it can probe naturally
    for whatever is still needed.
    """
    remaining = []
    for topic in topics:
        if topic.pk not in covered_topic_ids:
            goal_hint = f' Goal: "{topic.goal}"' if topic.goal else ""
            remaining.append(f"- {topic.name}.{goal_hint}")

    remaining_str = "\n".join(remaining) if remaining else "All topics covered!"
    covered_names = [t.name for t in topics if t.pk in covered_topic_ids]
    covered_str = ", ".join(covered_names) if covered_names else "None yet"

    system_prompt = f"""You are conducting a monthly work check-in interview. Be warm but concise.

TOPICS ALREADY COVERED: {covered_str}

TOPICS REMAINING:
{remaining_str}

INSTRUCTIONS:
1. Keep responses SHORT - one sentence, max two
2. Do NOT repeat or paraphrase what the user said
3. Do NOT say things like "I hear you", "That makes sense", "I understand"
4. Acknowledge briefly ("Got it." / "Thanks.") then move to the next topic
5. For remaining topics, ask questions that uncover the stated goal
6. If the user partially addressed a goal, probe naturally for what's still missing
7. When all topics are covered, thank them briefly and end the interview

Just respond naturally as the interviewer. No JSON, no special formatting."""

    return generate(system_prompt, user_message, history=chat_history)


def conduct_interview(user_message, chat_history, previously_covered_topic_ids):
    """
    Main interview function using the two-AI approach.
    1. Analyzer AI judges which topics are sufficiently covered based on their goals
    2. Interviewer AI generates a response and probes for what's still needed
    """
    from .models import Topic
    topics = list(Topic.objects.all())

    analysis = analyze_message(user_message, chat_history, topics)

    covered_topic_ids = list(previously_covered_topic_ids)
    topic_responses = {}

    for topic in topics:
        topic_analysis = analysis.get(str(topic.pk), {})
        if topic_analysis.get("covered") and topic.pk not in covered_topic_ids:
            covered_topic_ids.append(topic.pk)
            if topic_analysis.get("text"):
                topic_responses[topic.pk] = topic_analysis["text"]

    ai_response = generate_response(chat_history, user_message, topics, covered_topic_ids)

    interview_complete = all(t.pk in covered_topic_ids for t in topics)

    return {
        "response": ai_response,
        "covered_topics": covered_topic_ids,
        "topic_responses": topic_responses,
        "interview_complete": interview_complete,
    }
