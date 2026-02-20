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

    system_prompt = f"""You are conducting a friendly monthly work check-in. Be warm and conversational.

TOPICS ALREADY COVERED: {covered_str}

TOPICS REMAINING:
{remaining_str}

INSTRUCTIONS:
1. Ask ONE thing at a time — never combine questions
2. Keep responses SHORT - one sentence, max two
3. Do NOT repeat or paraphrase what the user said
4. Do NOT say things like "I hear you", "That makes sense", "I understand"
5. Acknowledge briefly ("Got it." / "Thanks.") then ask your next question
6. For each topic: first ask how they're feeling about it. Only ask why/what's driving it if they haven't already explained — probe naturally, don't front-load both questions
7. When all topics are covered, thank them briefly and end the interview

Just respond naturally as the interviewer. No JSON, no special formatting."""

    return generate(system_prompt, user_message, history=chat_history)


def generate_opening_question(topics):
    """Generate the AI's opening question before the respondent has said anything."""
    first_topic = topics[0].name if topics else "how things are going"

    system_prompt = f"""You are conducting a friendly work check-in. Be warm and natural.

Ask a simple, conversational opening question about {first_topic}.
One sentence only. Ask just how they're feeling — do NOT ask why or for reasons yet."""

    return generate(system_prompt, "Begin the interview.")


def conduct_interview(user_message, chat_history, previously_covered_topic_ids, interview=None):
    """
    Main interview function using the two-AI approach.
    1. Analyzer AI judges which topics are sufficiently covered based on their goals
    2. Interviewer AI generates a response and probes for what's still needed
    """
    from .models import Topic
    qs = Topic.objects.all() if interview is None else Topic.objects.filter(interview=interview)
    topics = list(qs)

    analysis = analyze_message(user_message, chat_history, topics)

    covered_topic_ids = list(previously_covered_topic_ids)
    topic_responses = {}

    for topic in topics:
        topic_analysis = analysis.get(str(topic.pk), {})
        if topic_analysis.get("covered") and topic.pk not in covered_topic_ids:
            covered_topic_ids.append(topic.pk)
            if topic_analysis.get("text"):
                topic_responses[topic.pk] = topic_analysis["text"]

    interview_complete = all(t.pk in covered_topic_ids for t in topics)

    if interview_complete:
        ai_response = "Thanks for sharing — that's everything! Your responses have been recorded."
    else:
        ai_response = generate_response(chat_history, user_message, topics, covered_topic_ids)

    return {
        "response": ai_response,
        "covered_topics": covered_topic_ids,
        "topic_responses": topic_responses,
        "interview_complete": interview_complete,
    }
