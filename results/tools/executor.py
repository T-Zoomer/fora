"""Tool dispatcher for executing tool calls."""

import json

from .sentiment_tools import get_sentiment_by_topic, compare_sentiment_across_topics
from .theme_tools import (
    get_themes_by_topic,
    get_sentiment_for_theme,
    correlate_themes_with_sentiment,
    find_common_themes_across_topics
)


TOOL_FUNCTIONS = {
    "get_sentiment_by_topic": get_sentiment_by_topic,
    "compare_sentiment_across_topics": compare_sentiment_across_topics,
    "get_themes_by_topic": get_themes_by_topic,
    "get_sentiment_for_theme": get_sentiment_for_theme,
    "correlate_themes_with_sentiment": correlate_themes_with_sentiment,
    "find_common_themes_across_topics": find_common_themes_across_topics,
}


def execute_tool(tool_name, arguments):
    """
    Execute a tool by name with given arguments.
    Returns the tool result as a JSON string.
    """
    if tool_name not in TOOL_FUNCTIONS:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    func = TOOL_FUNCTIONS[tool_name]

    try:
        # Parse arguments if they're a string
        if isinstance(arguments, str):
            arguments = json.loads(arguments) if arguments else {}

        result = func(**arguments)
        return json.dumps(result, default=str)
    except Exception as e:
        return json.dumps({"error": f"Tool execution failed: {str(e)}"})
