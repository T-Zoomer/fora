from collections import defaultdict
from math import sqrt

from questions.models import Answer, Question
from results.models import Result


def get_questions_with_results():
    """Get all questions that have analysis results."""
    results = Result.objects.filter(status='completed').select_related('question')
    questions = []
    for r in results:
        has_sentiment = bool(r.sentiment and r.sentiment.get('answers'))
        has_themes = bool(r.themes and len(r.themes) > 0)
        questions.append({
            'id': r.question.id,
            'text': r.question.text,
            'has_sentiment': has_sentiment,
            'has_themes': has_themes,
            'themes': [t['name'] for t in (r.themes or [])]
        })
    return questions


def get_respondent_sentiments(question_id):
    """Get respondent -> sentiment score mapping for a question."""
    result = Result.objects.filter(question_id=question_id, status='completed').first()
    if not result or not result.sentiment:
        return {}

    respondent_sentiments = {}
    for item in result.sentiment.get('answers', []):
        answer = Answer.objects.filter(id=item['id'], respondent__isnull=False).first()
        if answer:
            respondent_sentiments[answer.respondent_id] = item['score']
    return respondent_sentiments


def get_respondent_themes(question_id):
    """Get theme -> set of respondent IDs mapping for a question."""
    result = Result.objects.filter(question_id=question_id, status='completed').first()
    if not result or not result.themes:
        return {}, None

    theme_respondents = defaultdict(set)
    for theme in result.themes:
        theme_name = theme.get('name', 'Unknown')
        answer_ids = theme.get('answer_ids', [])
        answers = Answer.objects.filter(id__in=answer_ids, respondent__isnull=False)
        for answer in answers:
            theme_respondents[theme_name].add(answer.respondent_id)

    return dict(theme_respondents), result.question.text


def get_sentiment_correlation(target_question_id, source_question_ids):
    """
    Calculate point-biserial correlation between theme presence and sentiment score.

    Args:
        target_question_id: Question with sentiment scores
        source_question_ids: Questions to get themes from

    Returns correlation data.
    """
    # Get sentiment scores for target question
    respondent_sentiments = get_respondent_sentiments(target_question_id)

    if len(respondent_sentiments) < 3:
        return {'themes': [], 'respondent_count': len(respondent_sentiments)}

    # Get themes from source questions
    all_theme_respondents = {}
    theme_sources = {}

    for q_id in source_question_ids:
        if q_id == target_question_id:
            continue
        theme_respondents, q_text = get_respondent_themes(q_id)
        for theme_name, respondents in theme_respondents.items():
            # Filter to only respondents we have sentiment for
            valid_respondents = respondents & set(respondent_sentiments.keys())
            if valid_respondents:
                key = f"{theme_name}"
                if key in all_theme_respondents:
                    all_theme_respondents[key] |= valid_respondents
                else:
                    all_theme_respondents[key] = valid_respondents
                    theme_sources[key] = q_text[:40] if q_text else ''

    # Calculate stats
    all_respondent_ids = set(respondent_sentiments.keys())
    all_sentiments = list(respondent_sentiments.values())
    n = len(all_sentiments)

    mean_all = sum(all_sentiments) / n
    variance = sum((s - mean_all) ** 2 for s in all_sentiments) / n
    std_all = sqrt(variance) if variance > 0 else 0

    results = []

    for theme_name, respondents_with_theme in all_theme_respondents.items():
        n1 = len(respondents_with_theme)
        n0 = n - n1

        if n1 < 2 or n0 < 2:
            continue

        sentiments_with = [respondent_sentiments[r] for r in respondents_with_theme]
        mean_with = sum(sentiments_with) / n1

        respondents_without = all_respondent_ids - respondents_with_theme
        sentiments_without = [respondent_sentiments[r] for r in respondents_without]
        mean_without = sum(sentiments_without) / n0

        if std_all > 0:
            r_pb = ((mean_with - mean_without) / std_all) * sqrt((n1 * n0) / (n * n))
        else:
            r_pb = 0

        results.append({
            'name': theme_name,
            'correlation': round(r_pb, 3),
            'mean_with': round(mean_with, 2),
            'mean_without': round(mean_without, 2),
            'count': n1,
            'source': theme_sources.get(theme_name, '')
        })

    results.sort(key=lambda x: abs(x['correlation']), reverse=True)

    return {
        'themes': results,
        'respondent_count': n,
        'analysis_type': 'sentiment'
    }


def get_theme_correlation(target_question_id, target_theme, source_question_ids):
    """
    Calculate phi coefficient between theme presence in source and target theme presence.

    Args:
        target_question_id: Question containing the target theme
        target_theme: Theme name to explain
        source_question_ids: Questions to get source themes from

    Returns correlation data.
    """
    # Get respondents who have the target theme
    target_theme_respondents, _ = get_respondent_themes(target_question_id)

    if target_theme not in target_theme_respondents:
        return {'themes': [], 'respondent_count': 0, 'target_theme': target_theme}

    target_respondents = target_theme_respondents[target_theme]

    # Get all respondents who answered the target question (union of all theme respondents)
    all_target_respondents = set()
    for respondents in target_theme_respondents.values():
        all_target_respondents |= respondents

    if len(all_target_respondents) < 3:
        return {'themes': [], 'respondent_count': len(all_target_respondents), 'target_theme': target_theme}

    # Get themes from source questions
    all_theme_respondents = {}
    theme_sources = {}

    for q_id in source_question_ids:
        if q_id == target_question_id:
            continue
        theme_respondents, q_text = get_respondent_themes(q_id)
        for theme_name, respondents in theme_respondents.items():
            valid_respondents = respondents & all_target_respondents
            if valid_respondents:
                key = f"{theme_name}"
                if key in all_theme_respondents:
                    all_theme_respondents[key] |= valid_respondents
                else:
                    all_theme_respondents[key] = valid_respondents
                    theme_sources[key] = q_text[:40] if q_text else ''

    n = len(all_target_respondents)
    results = []

    for theme_name, source_respondents in all_theme_respondents.items():
        # Build 2x2 contingency table
        # n11 = has source theme AND has target theme
        # n10 = has source theme AND NOT target theme
        # n01 = NOT source theme AND has target theme
        # n00 = NOT source theme AND NOT target theme

        n11 = len(source_respondents & target_respondents)
        n10 = len(source_respondents - target_respondents)
        n01 = len(target_respondents - source_respondents)
        n00 = len(all_target_respondents - source_respondents - target_respondents)

        # Row and column totals
        n1_dot = n11 + n10  # has source theme
        n0_dot = n01 + n00  # no source theme
        n_dot1 = n11 + n01  # has target theme
        n_dot0 = n10 + n00  # no target theme

        # Phi coefficient
        denom = sqrt(n1_dot * n0_dot * n_dot1 * n_dot0)
        if denom > 0:
            phi = (n11 * n00 - n10 * n01) / denom
        else:
            phi = 0

        # Calculate lift for interpretability
        p_target = n_dot1 / n if n > 0 else 0
        p_target_given_source = n11 / n1_dot if n1_dot > 0 else 0
        lift = p_target_given_source / p_target if p_target > 0 else 1

        if n1_dot >= 2:
            results.append({
                'name': theme_name,
                'correlation': round(phi, 3),
                'lift': round(lift, 2),
                'co_occurrence': n11,
                'count': n1_dot,
                'source': theme_sources.get(theme_name, '')
            })

    results.sort(key=lambda x: abs(x['correlation']), reverse=True)

    return {
        'themes': results,
        'respondent_count': n,
        'target_theme': target_theme,
        'target_theme_count': len(target_respondents),
        'analysis_type': 'theme'
    }
