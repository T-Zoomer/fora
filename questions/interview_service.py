import json
from django.conf import settings
from openai import OpenAI

# Define interview topics with their requirements
INTERVIEW_TOPICS = [
    {
        "id": "general",
        "name": "General Check-in",
        "question": "How did it go at work this month?",
        "requires": ["assessment"],  # Just needs any substantive response
    },
    {
        "id": "productivity",
        "name": "Productivity",
        "question": "How has your productivity been?",
        "followup": "What's helped or gotten in the way?",
        "requires": ["assessment", "reason"],  # Needs both how + why
    },
    {
        "id": "wellbeing",
        "name": "Wellbeing",
        "question": "How have you been feeling about work?",
        "followup": "What's contributing to that?",
        "requires": ["assessment", "reason"],  # Needs both how + why
    },
]


def get_topics_status(covered_topics):
    """Return topics with their coverage status."""
    return [
        {
            "id": topic["id"],
            "name": topic["name"],
            "covered": topic["id"] in covered_topics
        }
        for topic in INTERVIEW_TOPICS
    ]


def get_opening_message():
    """Get the interviewer's opening message."""
    return "Hi! I'd like to check in with you about how work has been going. How did it go at work this month?"


def analyze_message(user_message, chat_history):
    """
    AI 1: Analyzer - Determines which topics the user's message addresses.

    This AI ONLY analyzes and outputs JSON. It doesn't converse.

    Returns:
        dict with topic coverage information:
        {
            "general": {"covered": bool, "text": str or None},
            "productivity": {"covered": bool, "has_assessment": bool, "has_reason": bool, "text": str or None},
            "wellbeing": {"covered": bool, "has_assessment": bool, "has_reason": bool, "text": str or None}
        }
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Build conversation context for the analyzer
    conversation_context = ""
    for msg in chat_history:
        role = "Interviewer" if msg["role"] == "assistant" else "User"
        conversation_context += f"{role}: {msg['content']}\n"
    conversation_context += f"User: {user_message}"

    system_prompt = """You analyze interview responses to determine which topics have been addressed.

TOPICS:
1. general - How work is going overall. Covered when user gives ANY substantive response about work.
2. productivity - How productive they've been AND why. Needs BOTH an assessment (good/bad/fine/etc) AND a reason (what helped or blocked).
3. wellbeing - How they're feeling AND why. Needs BOTH an assessment (good/bad/tired/stressed/etc) AND a reason (what's affecting their mood/energy).

IMPORTANT RULES:
- A topic can be covered in ANY message, even if not directly asked about it
- Look at the ENTIRE conversation, not just the latest message
- For productivity and wellbeing: if user only gives assessment without reason, mark has_assessment=true but covered=false
- Extract the user's EXACT words (or close paraphrase) as the "text" for each covered topic

Respond with ONLY valid JSON, no other text:
{
    "general": {"covered": true/false, "text": "user's exact words or null"},
    "productivity": {"covered": true/false, "has_assessment": true/false, "has_reason": true/false, "text": "user's exact words or null"},
    "wellbeing": {"covered": true/false, "has_assessment": true/false, "has_reason": true/false, "text": "user's exact words or null"}
}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Analyze this conversation:\n\n{conversation_context}"}
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=500,
        response_format={"type": "json_object"}  # Force JSON output
    )

    result_text = response.choices[0].message.content

    try:
        return json.loads(result_text)
    except json.JSONDecodeError:
        # Fallback: return empty analysis
        return {
            "general": {"covered": False, "text": None},
            "productivity": {"covered": False, "has_assessment": False, "has_reason": False, "text": None},
            "wellbeing": {"covered": False, "has_assessment": False, "has_reason": False, "text": None}
        }


def generate_response(chat_history, user_message, covered_topics, partial_topics):
    """
    AI 2: Interviewer - Generates a conversational response.

    This AI ONLY converses. No JSON output required.

    Args:
        chat_history: Previous messages
        user_message: Current user message
        covered_topics: List of fully covered topic IDs
        partial_topics: Dict of topics that are partially covered (e.g., {"productivity": "has assessment but no reason"})

    Returns:
        str: The interviewer's response
    """
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    # Build remaining topics description
    remaining = []
    for topic in INTERVIEW_TOPICS:
        if topic["id"] not in covered_topics:
            if topic["id"] in partial_topics:
                # Partially covered - need follow-up
                remaining.append(f"- {topic['name']}: {partial_topics[topic['id']]}")
            else:
                remaining.append(f"- {topic['name']}: not yet discussed")

    remaining_str = "\n".join(remaining) if remaining else "All topics covered!"
    covered_str = ", ".join(covered_topics) if covered_topics else "None yet"

    system_prompt = f"""You are conducting a monthly work check-in interview. Be warm but concise.

TOPICS ALREADY COVERED: {covered_str}

TOPICS REMAINING:
{remaining_str}

INSTRUCTIONS:
1. Keep responses SHORT - one sentence, max two
2. Do NOT repeat or paraphrase what the user said
3. Do NOT say things like "I hear you", "That makes sense", "I understand"
4. Acknowledge briefly ("Got it." / "Thanks.") then move to the next topic
5. If a topic is partially covered (has assessment but no reason), ask "What's made it that way?" or similar
6. When all topics are covered, thank them briefly and end the interview
7. Do NOT ask about topics that are already fully covered

Just respond naturally as the interviewer. No JSON, no special formatting."""

    messages = [{"role": "system", "content": system_prompt}]

    # Add chat history
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current user message
    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=200
    )

    return response.choices[0].message.content


def conduct_interview(user_message, chat_history, previously_covered_topics):
    """
    Main interview function using the two-AI approach.

    1. Analyzer AI determines which topics the user addressed
    2. Interviewer AI generates a response based on remaining topics

    Returns:
        dict with:
        - response: AI's response text
        - covered_topics: updated list of fully covered topic IDs
        - topic_responses: dict mapping topic_id to extracted text
        - interview_complete: bool indicating if all topics are covered
    """
    # Step 1: Analyze the user's message
    analysis = analyze_message(user_message, chat_history)

    # Step 2: Determine which topics are now covered
    covered_topics = list(previously_covered_topics)
    topic_responses = {}
    partial_topics = {}

    for topic_id in ["general", "productivity", "wellbeing"]:
        topic_analysis = analysis.get(topic_id, {})

        if topic_analysis.get("covered") and topic_id not in covered_topics:
            covered_topics.append(topic_id)
            if topic_analysis.get("text"):
                topic_responses[topic_id] = topic_analysis["text"]
        elif topic_id in ["productivity", "wellbeing"]:
            # Check for partial coverage
            has_assessment = topic_analysis.get("has_assessment", False)
            has_reason = topic_analysis.get("has_reason", False)
            if has_assessment and not has_reason and topic_id not in covered_topics:
                partial_topics[topic_id] = "gave assessment but needs to share why"

    # Step 3: Generate interviewer response
    ai_response = generate_response(chat_history, user_message, covered_topics, partial_topics)

    # Step 4: Check if interview is complete
    all_topic_ids = [t["id"] for t in INTERVIEW_TOPICS]
    interview_complete = all(tid in covered_topics for tid in all_topic_ids)

    return {
        "response": ai_response,
        "covered_topics": covered_topics,
        "topic_responses": topic_responses,
        "interview_complete": interview_complete,
        "analysis": analysis  # Include for debugging
    }
