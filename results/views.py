from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from questions.models import Question, Answer
from .models import Result
from .services import run_thematic_coding, run_sentiment_analysis, generate_summary, chat_with_answers
import json


def dashboard_view(request):
    """Main results dashboard."""
    questions = Question.objects.all()
    total_answers = Answer.objects.count()
    analyzed_count = Result.objects.filter(status='completed').count()

    # Check if processing is running
    is_running = Result.objects.filter(status='running').exists()

    return render(request, 'results/dashboard.html', {
        'questions_count': questions.count(),
        'total_answers': total_answers,
        'analyzed_count': analyzed_count,
        'is_running': is_running,
    })


@require_http_methods(["POST"])
def run_all_api(request):
    """Trigger processing for all questions."""
    questions = Question.objects.all()

    results = []
    for question in questions:
        # Skip questions with no answers
        answer_count = Answer.objects.filter(question=question).count()
        if answer_count == 0:
            continue

        # Get or create result
        result, _ = Result.objects.get_or_create(question=question)

        # Update status to running
        result.status = 'running'
        result.save()

        try:
            # Run thematic coding
            themes = run_thematic_coding(question)

            # Run sentiment analysis (if enabled for this question)
            sentiment = {}
            if question.analyze_sentiment:
                sentiment = run_sentiment_analysis(question)

            # Generate AI summary
            summary = generate_summary(question)

            # Save results
            result.themes = themes
            result.sentiment = sentiment
            result.summary = summary
            result.answer_count = answer_count
            result.status = 'completed'
            result.save()

            results.append({
                'question_id': question.id,
                'status': 'completed',
                'themes_count': len(themes),
                'sentiment_avg': sentiment.get('average'),
            })
        except Exception as e:
            result.status = 'failed'
            result.save()
            results.append({
                'question_id': question.id,
                'status': 'failed',
                'error': str(e),
            })

    return JsonResponse({
        'success': True,
        'results': results,
    })


@require_http_methods(["GET"])
def get_all_results_api(request):
    """Get results for all questions."""
    questions = Question.objects.all().order_by('order')

    all_results = []
    for question in questions:
        result = Result.objects.filter(question=question).first()
        answers = {str(a.id): a.text for a in Answer.objects.filter(question=question)}

        if not result or result.status != 'completed':
            all_results.append({
                'question_id': question.id,
                'question_text': question.text,
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
            'question_id': question.id,
            'question_text': question.text,
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
    """Chat with the answers of a specific question."""
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        message = data.get('message', '').strip()
        chat_history = data.get('history', [])

        if not question_id:
            return JsonResponse({'error': 'question_id is required'}, status=400)
        if not message:
            return JsonResponse({'error': 'message is required'}, status=400)

        question = Question.objects.filter(id=question_id).first()
        if not question:
            return JsonResponse({'error': 'Question not found'}, status=404)

        response_text = chat_with_answers(question, message, chat_history)

        return JsonResponse({
            'success': True,
            'response': response_text
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
