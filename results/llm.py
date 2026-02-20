"""
LLM provider abstraction.

To switch provider, change PROVIDER to "openai", "gemini", or "anthropic".
To switch model, change the corresponding entry in MODELS.
"""

import re


def _strip_fences(text):
    """Strip markdown code fences that some models wrap responses in."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()

PROVIDER = "gemini"

MODELS = {
    "openai": "gpt-4o",
    "gemini": "gemini-3-flash-preview",
    "anthropic": "claude-sonnet-4-6",
}


def generate(system_prompt, user_prompt, json_mode=False, history=None):
    """
    Generate a response from the configured LLM provider.

    Args:
        system_prompt: The system/instruction prompt.
        user_prompt: The user message / content to analyze.
        json_mode: If True, instructs the model to return valid JSON.
        history: Optional list of prior messages [{"role": "user"|"assistant", "content": str}]
                 for multi-turn conversations.

    Returns:
        The model's response as a string.
    """
    from django.conf import settings

    model = MODELS[PROVIDER]
    history = history or []

    if PROVIDER == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_prompt})
        kwargs = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content

    if PROVIDER == "gemini":
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        if history:
            contents = []
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))
            contents.append(types.Content(role="user", parts=[types.Part(text=user_prompt)]))
        else:
            contents = user_prompt
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json" if json_mode else "text/plain",
            ),
        )
        return response.text

    if PROVIDER == "anthropic":
        import anthropic
        sys = system_prompt
        if json_mode:
            sys += "\n\nRespond only with valid JSON. No other text."
        messages = []
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_prompt})
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=model,
            max_tokens=8192,
            system=sys,
            messages=messages,
        )
        return _strip_fences(response.content[0].text)

    raise ValueError(f"Unknown LLM provider: {PROVIDER!r}")
