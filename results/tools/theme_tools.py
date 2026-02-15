"""Theme analysis tools for correlation analysis."""

import statistics
from collections import defaultdict

from questions.models import Interview, Answer
from results.models import Result


def get_themes_by_topic(topic_ids=None):
    """
    List themes with frequencies for interview topics.
    """
    if topic_ids:
        results = Result.objects.filter(interview_id__in=topic_ids).select_related('interview')
    else:
        results = Result.objects.all().select_related('interview')

    output = {"topics": []}

    for result in results:
        themes = result.themes or []

        if not themes:
            continue

        # Get total answer count for percentage calculation
        total_answers = result.answer_count or 1

        theme_list = []
        for theme in themes:
            answer_count = len(theme.get("answer_ids", []))
            theme_list.append({
                "name": theme.get("name", ""),
                "description": theme.get("description", ""),
                "count": answer_count,
                "percentage": round(answer_count / total_answers * 100, 1)
            })

        # Sort by count descending
        theme_list.sort(key=lambda x: x["count"], reverse=True)

        output["topics"].append({
            "topic_id": result.interview_id,
            "topic_name": result.interview.text,
            "total_answers": total_answers,
            "themes": theme_list
        })

    return output


def get_sentiment_for_theme(topic_id, theme_name):
    """
    Get sentiment for answers containing a specific theme.
    """
    try:
        result = Result.objects.select_related('interview').get(interview_id=topic_id)
    except Result.DoesNotExist:
        return {"error": f"No results found for topic ID {topic_id}"}

    themes = result.themes or []
    sentiment_data = result.sentiment or {}
    answer_scores = sentiment_data.get("answers", [])

    # Find matching theme (case-insensitive partial match)
    theme_name_lower = theme_name.lower()
    matching_theme = None
    for theme in themes:
        if theme_name_lower in theme.get("name", "").lower():
            matching_theme = theme
            break

    if not matching_theme:
        available_themes = [t.get("name", "") for t in themes]
        return {
            "error": f"Theme '{theme_name}' not found",
            "available_themes": available_themes
        }

    # Get answer IDs for this theme
    theme_answer_ids = set(matching_theme.get("answer_ids", []))

    # Build answer_id to score mapping
    answer_id_to_score = {a["id"]: a["score"] for a in answer_scores}

    # Get scores for theme answers
    theme_scores = [answer_id_to_score[aid] for aid in theme_answer_ids if aid in answer_id_to_score]

    if not theme_scores:
        return {
            "theme": matching_theme.get("name"),
            "error": "No sentiment scores found for theme answers"
        }

    # Calculate overall topic average for comparison
    all_scores = [a["score"] for a in answer_scores]
    topic_average = statistics.mean(all_scores) if all_scores else 0

    # Get sample answers
    sample_answer_ids = list(theme_answer_ids)[:3]
    sample_answers = list(Answer.objects.filter(id__in=sample_answer_ids).values('id', 'text'))

    # Add sentiment scores to samples
    for sample in sample_answers:
        sample["sentiment_score"] = answer_id_to_score.get(sample["id"])

    return {
        "topic_name": result.interview.text,
        "theme": matching_theme.get("name"),
        "theme_description": matching_theme.get("description"),
        "sentiment": {
            "average": round(statistics.mean(theme_scores), 2),
            "min": min(theme_scores),
            "max": max(theme_scores),
            "count": len(theme_scores)
        },
        "comparison": {
            "topic_average": round(topic_average, 2),
            "difference": round(statistics.mean(theme_scores) - topic_average, 2)
        },
        "sample_answers": sample_answers
    }


def correlate_themes_with_sentiment(topic_ids=None, sentiment_filter="all"):
    """
    Find themes associated with high/low sentiment.
    """
    if topic_ids:
        results = Result.objects.filter(interview_id__in=topic_ids).select_related('interview')
    else:
        results = Result.objects.all().select_related('interview')

    theme_sentiments = []

    for result in results:
        themes = result.themes or []
        sentiment_data = result.sentiment or {}
        answer_scores = sentiment_data.get("answers", [])

        if not themes or not answer_scores:
            continue

        # Build answer_id to score mapping
        answer_id_to_score = {a["id"]: a["score"] for a in answer_scores}

        for theme in themes:
            theme_answer_ids = theme.get("answer_ids", [])
            theme_scores = [answer_id_to_score[aid] for aid in theme_answer_ids if aid in answer_id_to_score]

            if not theme_scores:
                continue

            avg_sentiment = statistics.mean(theme_scores)

            # Apply sentiment filter
            if sentiment_filter == "low" and avg_sentiment > 4:
                continue
            if sentiment_filter == "high" and avg_sentiment < 7:
                continue

            theme_sentiments.append({
                "topic_id": result.interview_id,
                "topic_name": result.interview.text,
                "theme": theme.get("name"),
                "description": theme.get("description"),
                "average_sentiment": round(avg_sentiment, 2),
                "answer_count": len(theme_scores),
                "sentiment_category": _categorize_sentiment(avg_sentiment)
            })

    # Sort by sentiment (low to high for "low" filter, high to low for "high" filter)
    if sentiment_filter == "low":
        theme_sentiments.sort(key=lambda x: x["average_sentiment"])
    else:
        theme_sentiments.sort(key=lambda x: x["average_sentiment"], reverse=True)

    return {
        "filter": sentiment_filter,
        "themes": theme_sentiments,
        "summary": _summarize_theme_sentiments(theme_sentiments, sentiment_filter)
    }


def find_common_themes_across_topics(topic_ids=None):
    """
    Identify similar themes across different interview topics.
    """
    if topic_ids:
        results = Result.objects.filter(interview_id__in=topic_ids).select_related('interview')
    else:
        results = Result.objects.all().select_related('interview')

    # Collect all themes by topic
    all_themes = []
    for result in results:
        themes = result.themes or []
        for theme in themes:
            all_themes.append({
                "topic_id": result.interview_id,
                "topic_name": result.interview.text,
                "theme_name": theme.get("name", ""),
                "description": theme.get("description", ""),
                "answer_count": len(theme.get("answer_ids", []))
            })

    if not all_themes:
        return {"clusters": [], "message": "No themes found"}

    # Group themes by similarity (simple word overlap for now)
    clusters = _cluster_similar_themes(all_themes)

    return {
        "clusters": clusters,
        "total_themes": len(all_themes),
        "topics_analyzed": results.count()
    }


def _categorize_sentiment(score):
    """Categorize sentiment score."""
    if score <= 4:
        return "negative"
    if score <= 6:
        return "neutral"
    return "positive"


def _summarize_theme_sentiments(theme_sentiments, filter_type):
    """Generate summary of theme sentiments."""
    if not theme_sentiments:
        return "No themes found matching the filter criteria."

    if filter_type == "low":
        top_themes = theme_sentiments[:3]
        return f"Top {len(top_themes)} themes with lowest sentiment: " + ", ".join(
            f"{t['theme']} ({t['average_sentiment']})" for t in top_themes
        )
    elif filter_type == "high":
        top_themes = theme_sentiments[:3]
        return f"Top {len(top_themes)} themes with highest sentiment: " + ", ".join(
            f"{t['theme']} ({t['average_sentiment']})" for t in top_themes
        )
    else:
        low = [t for t in theme_sentiments if t["sentiment_category"] == "negative"]
        high = [t for t in theme_sentiments if t["sentiment_category"] == "positive"]
        return f"Found {len(low)} themes with negative sentiment and {len(high)} with positive sentiment."


def _cluster_similar_themes(themes):
    """
    Cluster similar themes across topics using word overlap.
    Returns clusters of related themes.
    """
    from collections import defaultdict

    # Extract significant words from theme names
    def get_words(name):
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with'}
        words = set(name.lower().replace('-', ' ').replace('_', ' ').split())
        return words - stop_words

    # Group themes that share significant words
    word_to_themes = defaultdict(list)
    for theme in themes:
        words = get_words(theme["theme_name"])
        for word in words:
            if len(word) > 2:  # Skip very short words
                word_to_themes[word].append(theme)

    # Find clusters (themes appearing together via shared words)
    clusters = []
    seen_themes = set()

    for word, word_themes in sorted(word_to_themes.items(), key=lambda x: -len(x[1])):
        if len(word_themes) < 2:  # Only cluster if theme appears in 2+ topics
            continue

        # Check if themes span multiple topics
        topic_ids = set(t["topic_id"] for t in word_themes)
        if len(topic_ids) < 2:
            continue

        # Create cluster key
        cluster_key = tuple(sorted((t["topic_id"], t["theme_name"]) for t in word_themes))
        if cluster_key in seen_themes:
            continue
        seen_themes.add(cluster_key)

        clusters.append({
            "shared_concept": word,
            "themes": [
                {
                    "topic_name": t["topic_name"],
                    "theme": t["theme_name"],
                    "answer_count": t["answer_count"]
                }
                for t in word_themes
            ],
            "topic_count": len(topic_ids)
        })

    # Sort by number of topics covered
    clusters.sort(key=lambda x: (-x["topic_count"], -len(x["themes"])))

    return clusters[:10]  # Return top 10 clusters
