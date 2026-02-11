from django.http import JsonResponse
from django.shortcuts import render

from .services import (
    get_questions_with_results,
    get_sentiment_correlation,
    get_theme_correlation,
)


def dashboard_view(request):
    """Main analysis dashboard."""
    return render(request, 'analysis/dashboard.html')


def questions_api(request):
    """Returns available questions with their analysis capabilities."""
    questions = get_questions_with_results()
    return JsonResponse({'questions': questions})


def correlation_api(request):
    """
    Returns correlation data.

    Query params:
        target: target question ID
        sources: comma-separated source question IDs (optional, defaults to all others)
        target_theme: theme name to explain (required if target has no sentiment)
    """
    target_id = request.GET.get('target')
    sources = request.GET.get('sources', '')
    target_theme = request.GET.get('target_theme', '')

    if not target_id:
        return JsonResponse({'error': 'target parameter required'}, status=400)

    try:
        target_id = int(target_id)
    except ValueError:
        return JsonResponse({'error': 'invalid target parameter'}, status=400)

    # Parse source IDs
    questions = get_questions_with_results()
    all_question_ids = [q['id'] for q in questions]

    if sources:
        try:
            source_ids = [int(s) for s in sources.split(',')]
        except ValueError:
            return JsonResponse({'error': 'invalid sources parameter'}, status=400)
    else:
        source_ids = [q_id for q_id in all_question_ids if q_id != target_id]

    # Determine analysis type based on target question
    target_question = next((q for q in questions if q['id'] == target_id), None)
    if not target_question:
        return JsonResponse({'error': 'target question not found'}, status=404)

    if target_question['has_sentiment']:
        # Sentiment correlation
        data = get_sentiment_correlation(target_id, source_ids)
    elif target_theme:
        # Theme correlation
        data = get_theme_correlation(target_id, target_theme, source_ids)
    else:
        return JsonResponse({
            'error': 'target_theme required for questions without sentiment',
            'available_themes': target_question['themes']
        }, status=400)

    data['target_question'] = target_question['text']
    return JsonResponse(data)
