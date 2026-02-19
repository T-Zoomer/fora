from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from questions.models import Interview, Answer
from .models import Result
from .services import run_thematic_coding, run_sentiment_analysis, generate_summary, chat_with_all_answers, discover_themes_only, run_classification_with_themes
import json


def dashboard_view(request):
    """Main results dashboard."""
    # Clear any results stuck in transient statuses from a previous server session
    Result.objects.filter(status__in=['running', 'discovering', 'classifying']).update(status='failed')
    Result.objects.filter(status='editing').update(status='completed')

    interviews = Interview.objects.all()
    total_answers = Answer.objects.count()
    analyzed_count = Result.objects.filter(status='completed').count()

    return render(request, 'results/dashboard.html', {
        'interviews_count': interviews.count(),
        'total_answers': total_answers,
        'analyzed_count': analyzed_count,
    })


@require_http_methods(["POST"])
def run_single_api(request, interview_id):
    """Trigger processing for a single interview."""
    try:
        interview = Interview.objects.get(id=interview_id)
    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found'}, status=404)

    answer_count = Answer.objects.filter(interview=interview).count()
    if answer_count == 0:
        return JsonResponse({'error': 'No answers to analyze'}, status=400)

    result, _ = Result.objects.get_or_create(interview=interview)
    result.status = 'running'
    result.save()

    try:
        proposed = discover_themes_only(interview)
        result.proposed_themes = proposed
        result.save()

        themes = run_classification_with_themes(interview, proposed)
        sentiment = {}
        if interview.analyze_sentiment:
            sentiment = run_sentiment_analysis(interview)
        summary = generate_summary(interview)

        result.themes = themes
        result.sentiment = sentiment
        result.summary = summary
        result.answer_count = answer_count
        result.status = 'completed'
        result.save()

        return JsonResponse({
            'success': True,
            'interview_id': interview.id,
            'status': 'completed',
            'themes_count': len(themes),
        })
    except Exception as e:
        import traceback
        print(f"[error] interview {interview.id}: {e}")
        traceback.print_exc()
        result.status = 'failed'
        result.save()
        return JsonResponse({
            'success': False,
            'interview_id': interview.id,
            'status': 'failed',
            'error': str(e),
        }, status=500)


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
            import traceback
            print(f"[error] interview {interview.id}: {e}")
            traceback.print_exc()
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
def get_answers_api(request, interview_id):
    """Return all answers for an interview (for the quote wall)."""
    try:
        interview = Interview.objects.get(id=interview_id)
    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found'}, status=404)

    answers = list(Answer.objects.filter(interview=interview).values('id', 'text'))
    return JsonResponse({'answers': answers})


@require_http_methods(["POST"])
def discover_themes_api(request, interview_id):
    """Run Pass 1 (theme discovery) and save proposed_themes; set status='editing'."""
    try:
        interview = Interview.objects.get(id=interview_id)
    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found'}, status=404)

    answer_count = Answer.objects.filter(interview=interview).count()
    if answer_count == 0:
        return JsonResponse({'error': 'No answers to analyze'}, status=400)

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}
    custom_prompt = body.get('custom_prompt', '') or ''

    result, _ = Result.objects.get_or_create(interview=interview)
    result.status = 'discovering'
    result.save()

    try:
        themes = discover_themes_only(interview, custom_prompt=custom_prompt or None)
        result.proposed_themes = themes
        result.status = 'editing'
        result.save()

        return JsonResponse({
            'success': True,
            'interview_id': interview.id,
            'status': 'editing',
            'proposed_themes': themes,
        })
    except Exception as e:
        import traceback
        print(f"[error] discover interview {interview.id}: {e}")
        traceback.print_exc()
        result.status = 'failed'
        result.save()
        return JsonResponse({
            'success': False,
            'interview_id': interview.id,
            'status': 'failed',
            'error': str(e),
        }, status=500)


@require_http_methods(["POST"])
def classify_with_themes_api(request, interview_id):
    """Run Pass 2 with user-edited themes; set status='completed'."""
    try:
        interview = Interview.objects.get(id=interview_id)
    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found'}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    themes_input = data.get('themes', [])
    if not themes_input:
        return JsonResponse({'error': 'themes is required'}, status=400)

    answer_count = Answer.objects.filter(interview=interview).count()
    result, _ = Result.objects.get_or_create(interview=interview)
    result.status = 'classifying'
    result.save()

    try:
        full_themes = run_classification_with_themes(interview, themes_input)

        sentiment = {}
        if interview.analyze_sentiment:
            sentiment = run_sentiment_analysis(interview)
        summary = generate_summary(interview)

        result.themes = full_themes
        result.proposed_themes = themes_input  # save the final user-edited set
        result.sentiment = sentiment
        result.summary = summary
        result.answer_count = answer_count
        result.status = 'completed'
        result.save()

        return JsonResponse({
            'success': True,
            'interview_id': interview.id,
            'status': 'completed',
            'themes_count': len(full_themes),
        })
    except Exception as e:
        import traceback
        print(f"[error] classify interview {interview.id}: {e}")
        traceback.print_exc()
        result.status = 'failed'
        result.save()
        return JsonResponse({
            'success': False,
            'interview_id': interview.id,
            'status': 'failed',
            'error': str(e),
        }, status=500)


@require_http_methods(["GET"])
def get_all_results_api(request):
    """Get results for all interviews."""
    interviews = Interview.objects.all().order_by('order')

    all_results = []
    for interview in interviews:
        result = Result.objects.filter(interview=interview).first()
        answers = {str(a.id): a.text for a in Answer.objects.filter(interview=interview)}

        if not result or result.status not in ('completed', 'classifying'):
            all_results.append({
                'interview_id': interview.id,
                'interview_text': interview.text,
                'status': result.status if result else 'pending',
                'answer_count': len(answers),
                'themes': [],
                'proposed_themes': result.proposed_themes if result else [],
            })
            continue

        # Enrich themes with answer texts and excerpts
        themes_with_texts = []
        for theme in result.themes:
            theme_copy = theme.copy()
            all_answers = [
                {
                    'id': aid,
                    'text': answers.get(str(aid), ''),
                    'excerpt': theme.get('excerpts', {}).get(str(aid), ''),
                }
                for aid in theme.get('answer_ids', [])
            ]
            theme_copy['count'] = len(all_answers)
            theme_copy['answers'] = all_answers[:8]
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
            'proposed_themes': result.proposed_themes,
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
