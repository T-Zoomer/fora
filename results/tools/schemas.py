"""OpenAI tool definitions for correlation analysis."""

CHAT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_sentiment_by_topic",
            "description": "Get sentiment statistics (average, min, max, distribution) for interview topics. Use this to understand overall sentiment levels for specific topics or all topics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional list of interview IDs to analyze. If not provided, analyzes all topics."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_sentiment_across_topics",
            "description": "Compare sentiment between two or more topics and calculate correlation coefficient. Use this to see if sentiment in one topic correlates with another (e.g., does productivity correlate with wellbeing?).",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of 2 or more interview IDs to compare."
                    }
                },
                "required": ["topic_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_themes_by_topic",
            "description": "List themes with their frequencies for interview topics. Use this to see what themes are present and how common they are.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional list of interview IDs. If not provided, returns themes for all topics."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sentiment_for_theme",
            "description": "Get sentiment statistics for answers containing a specific theme. Use this to understand how people who mentioned a specific theme feel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic_id": {
                        "type": "integer",
                        "description": "The interview ID to analyze."
                    },
                    "theme_name": {
                        "type": "string",
                        "description": "The name of the theme to analyze (case-insensitive partial match)."
                    }
                },
                "required": ["topic_id", "theme_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "correlate_themes_with_sentiment",
            "description": "Find which themes are associated with high or low sentiment. Use this to identify what factors drive positive or negative feelings.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional list of interview IDs. If not provided, analyzes all topics."
                    },
                    "sentiment_filter": {
                        "type": "string",
                        "enum": ["all", "low", "high"],
                        "description": "Filter themes by sentiment: 'low' (1-4), 'high' (7-10), or 'all'. Default is 'all'."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_common_themes_across_topics",
            "description": "Identify similar themes that appear across different interview topics. Use this to find patterns that span multiple topics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Optional list of interview IDs. If not provided, analyzes all topics."
                    }
                },
                "required": []
            }
        }
    }
]
