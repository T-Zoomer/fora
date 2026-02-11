from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from questions.models import Interview, Answer
from .models import Result
from .services import run_thematic_coding, run_sentiment_analysis, generate_summary, chat_with_all_answers
import json


def dashboard_view(request):
    """Main results dashboard."""
    interviews = Interview.objects.all()
    total_answers = Answer.objects.count()
    analyzed_count = Result.objects.filter(status='completed').count()

    # Check if processing is running
    is_running = Result.objects.filter(status='running').exists()

    return render(request, 'results/dashboard.html', {
        'interviews_count': interviews.count(),
        'total_answers': total_answers,
        'analyzed_count': analyzed_count,
        'is_running': is_running,
    })


@require_http_methods(["POST"])
def run_all_api(request):
    """Trigger processing for all interviews."""
    interviews = Interview.objects.all()

    results = []
    for interview in interviews:
        # Skip interviews with no answers
        answer_count = Answer.objects.filter(interview=interview).count()
        if answer_count == 0:
            continue

        # Get or create result
        result, _ = Result.objects.get_or_create(interview=interview)

        # Update status to running
        result.status = 'running'
        result.save()

        try:
            # Run thematic coding
            themes = run_thematic_coding(interview)

            # Run sentiment analysis (if enabled for this interview)
            sentiment = {}
            if interview.analyze_sentiment:
                sentiment = run_sentiment_analysis(interview)

            # Generate AI summary
            summary = generate_summary(interview)

            # Save results
            result.themes = themes
            result.sentiment = sentiment
            result.summary = summary
            result.answer_count = answer_count
            result.status = 'completed'
            result.save()

            results.append({
                'interview_id': interview.id,
                'status': 'completed',
                'themes_count': len(themes),
                'sentiment_avg': sentiment.get('average'),
            })
        except Exception as e:
            result.status = 'failed'
            result.save()
            results.append({
                'interview_id': interview.id,
                'status': 'failed',
                'error': str(e),
            })

    return JsonResponse({
        'success': True,
        'results': results,
    })


@require_http_methods(["GET"])
def get_all_results_api(request):
    """Get results for all interviews."""
    interviews = Interview.objects.all().order_by('order')

    all_results = []
    for interview in interviews:
        result = Result.objects.filter(interview=interview).first()
        answers = {str(a.id): a.text for a in Answer.objects.filter(interview=interview)}

        if not result or result.status != 'completed':
            all_results.append({
                'interview_id': interview.id,
                'interview_text': interview.text,
                'status': result.status if result else 'not_analyzed',
                'answer_count': len(answers),
                'themes': [],
            })
            continue

        # Enrich themes with answer texts
        themes_with_texts = []
        for theme in result.themes:
            theme_copy = theme.copy()
            theme_copy['answers'] = [
                {'id': aid, 'text': answers.get(str(aid), '')}
                for aid in theme.get('answer_ids', [])
            ]
            theme_copy['count'] = len(theme_copy['answers'])
            themes_with_texts.append(theme_copy)

        all_results.append({
            'interview_id': interview.id,
            'interview_text': interview.text,
            'status': result.status,
            'analyzed_at': result.analyzed_at.isoformat() if result.analyzed_at else None,
            'answer_count': result.answer_count,
            'summary': result.summary,
            'themes': themes_with_texts,
            'sentiment': result.sentiment,
        })

    return JsonResponse({'results': all_results})


@require_http_methods(["POST"])
def chat_api(request):
    """Chat with all survey answers."""
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        chat_history = data.get('history', [])

        if not message:
            return JsonResponse({'error': 'message is required'}, status=400)

        response_text = chat_with_all_answers(message, chat_history)

        return JsonResponse({
            'success': True,
            'response': response_text
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
