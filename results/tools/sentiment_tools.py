"""Sentiment analysis tools for correlation analysis."""

import statistics
from collections import defaultdict

from questions.models import Interview, Answer
from results.models import Result


def get_sentiment_by_topic(topic_ids=None):
    """
    Get sentiment stats (avg, min, max, distribution) for interview topics.
    """
    if topic_ids:
        results = Result.objects.filter(interview_id__in=topic_ids).select_related('interview')
    else:
        results = Result.objects.all().select_related('interview')

    output = {"topics": []}

    for result in results:
        sentiment_data = result.sentiment or {}
        answer_scores = sentiment_data.get("answers", [])

        if not answer_scores:
            continue

        scores = [a["score"] for a in answer_scores]

        # Calculate distribution buckets
        distribution = {
            "low (1-4)": len([s for s in scores if 1 <= s <= 4]),
            "neutral (5-6)": len([s for s in scores if 5 <= s <= 6]),
            "high (7-10)": len([s for s in scores if 7 <= s <= 10])
        }

        topic_stats = {
            "topic_id": result.interview_id,
            "topic_name": result.interview.text,
            "average": round(statistics.mean(scores), 2),
            "min": min(scores),
            "max": max(scores),
            "std_dev": round(statistics.stdev(scores), 2) if len(scores) > 1 else 0,
            "count": len(scores),
            "distribution": distribution
        }
        output["topics"].append(topic_stats)

    # Sort by average sentiment
    output["topics"].sort(key=lambda x: x["average"])

    return output


def compare_sentiment_across_topics(topic_ids):
    """
    Compare sentiment between topics with Pearson correlation coefficient.
    Requires at least 2 topic IDs.
    """
    if not topic_ids or len(topic_ids) < 2:
        return {"error": "At least 2 topic IDs are required for comparison"}

    results = Result.objects.filter(interview_id__in=topic_ids).select_related('interview')

    if results.count() < 2:
        return {"error": "Not enough topics found with sentiment data"}

    # Build respondent-to-score mapping for each topic
    topic_scores = {}
    topic_names = {}

    for result in results:
        sentiment_data = result.sentiment or {}
        answer_scores = sentiment_data.get("answers", [])

        if not answer_scores:
            continue

        topic_names[result.interview_id] = result.interview.text

        # Map answer_id to score
        answer_id_to_score = {a["id"]: a["score"] for a in answer_scores}

        # Get respondent for each answer
        answers = Answer.objects.filter(id__in=answer_id_to_score.keys()).select_related('respondent')
        respondent_scores = {}
        for answer in answers:
            if answer.respondent_id:
                respondent_scores[answer.respondent_id] = answer_id_to_score[answer.id]

        topic_scores[result.interview_id] = {
            "name": result.interview.text,
            "scores": [a["score"] for a in answer_scores],
            "respondent_scores": respondent_scores
        }

    # Calculate per-topic averages
    comparisons = []
    for tid, data in topic_scores.items():
        if data["scores"]:
            comparisons.append({
                "topic_id": tid,
                "topic_name": data["name"],
                "average": round(statistics.mean(data["scores"]), 2),
                "count": len(data["scores"])
            })

    # Calculate pairwise correlations for topics with matching respondents
    correlations = []
    topic_id_list = list(topic_scores.keys())

    for i in range(len(topic_id_list)):
        for j in range(i + 1, len(topic_id_list)):
            tid1, tid2 = topic_id_list[i], topic_id_list[j]
            resp1 = topic_scores[tid1]["respondent_scores"]
            resp2 = topic_scores[tid2]["respondent_scores"]

            # Find common respondents
            common_respondents = set(resp1.keys()) & set(resp2.keys())

            if len(common_respondents) >= 3:
                scores1 = [resp1[r] for r in common_respondents]
                scores2 = [resp2[r] for r in common_respondents]

                correlation = _pearson_correlation(scores1, scores2)

                correlations.append({
                    "topic1": topic_names[tid1],
                    "topic2": topic_names[tid2],
                    "correlation": round(correlation, 2) if correlation is not None else None,
                    "matched_respondents": len(common_respondents),
                    "interpretation": _interpret_correlation(correlation)
                })
            else:
                correlations.append({
                    "topic1": topic_names[tid1],
                    "topic2": topic_names[tid2],
                    "correlation": None,
                    "matched_respondents": len(common_respondents),
                    "interpretation": "Not enough matched respondents for correlation"
                })

    return {
        "topics": comparisons,
        "correlations": correlations
    }


def _pearson_correlation(x, y):
    """Calculate Pearson correlation coefficient between two lists."""
    if len(x) != len(y) or len(x) < 2:
        return None

    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n

    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    denominator_x = sum((x[i] - mean_x) ** 2 for i in range(n))
    denominator_y = sum((y[i] - mean_y) ** 2 for i in range(n))

    denominator = (denominator_x * denominator_y) ** 0.5

    if denominator == 0:
        return None

    return numerator / denominator


def _interpret_correlation(r):
    """Provide human-readable interpretation of correlation coefficient."""
    if r is None:
        return "Unable to calculate"
    if r >= 0.7:
        return "Strong positive correlation"
    if r >= 0.4:
        return "Moderate positive correlation"
    if r >= 0.2:
        return "Weak positive correlation"
    if r > -0.2:
        return "No significant correlation"
    if r > -0.4:
        return "Weak negative correlation"
    if r > -0.7:
        return "Moderate negative correlation"
    return "Strong negative correlation"
