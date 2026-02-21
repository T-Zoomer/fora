import json
import traceback

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods


from django.utils import timezone

from interview.models import Topic, Answer, Interview, InterviewSession
from .models import Result
from .services import run_sentiment_analysis, generate_summary, chat_with_all_answers, discover_themes_only, run_classification_with_themes


def results_redirect_view(request):
    interview = Interview.objects.order_by('created_at').first()
    if interview is None:
        from django.http import Http404
        raise Http404
    return redirect(f'/results/{interview.uuid}/')


def dashboard_view(request, interview_id):
    """Main results dashboard."""
    interview = get_object_or_404(Interview, uuid=interview_id)

    if interview.is_open:
        return render(request, 'results/tracking.html', {'interview': interview})

    # Clear any results stuck in transient statuses from a previous server session
    Result.objects.filter(status__in=['running', 'discovering', 'classifying']).update(status='failed')
    Result.objects.filter(status='editing').update(status='completed')

    topics = Topic.objects.filter(interview=interview)
    total_answers = Answer.objects.filter(topic__interview=interview).count()
    analyzed_count = Result.objects.filter(topic__interview=interview, status='completed').count()

    return render(request, 'results/dashboard.html', {
        'interview': interview,
        'interview_id': interview_id,
        'topics_count': topics.count(),
        'total_answers': total_answers,
        'analyzed_count': analyzed_count,
    })


def _run_topic_pipeline(topic, result, answer_count):
    """Run the full analysis pipeline for a topic. Mutates and saves result."""
    proposed = discover_themes_only(topic)
    result.proposed_themes = proposed
    result.save()

    themes = run_classification_with_themes(topic, proposed)
    sentiment = {}
    if topic.analyze_sentiment:
        sentiment = run_sentiment_analysis(topic)
    summary = generate_summary(topic)

    result.themes = themes
    result.sentiment = sentiment
    result.summary = summary
    result.answer_count = answer_count
    result.analyzed_at = timezone.now()
    result.status = 'completed'
    result.save()


@require_http_methods(["POST"])
def close_interview_api(request, interview_id):
    """Close interview and run analysis on all topics."""
    interview = get_object_or_404(Interview, uuid=interview_id)
    interview.is_open = False
    interview.save(update_fields=['is_open'])

    for topic in Topic.objects.filter(interview=interview):
        answer_count = Answer.objects.filter(topic=topic).count()
        if answer_count == 0:
            continue
        result, _ = Result.objects.get_or_create(topic=topic)
        result.status = 'running'
        result.save()
        try:
            _run_topic_pipeline(topic, result, answer_count)
        except Exception as e:
            print(f"[error] close-analyse topic {topic.id}: {e}")
            traceback.print_exc()
            result.status = 'failed'
            result.save()

    return JsonResponse({'success': True})


@require_http_methods(["GET"])
def sessions_api(request, interview_id):
    interview = get_object_or_404(Interview, uuid=interview_id)
    completed = InterviewSession.objects.filter(interview=interview).count()
    return JsonResponse({'completed': completed})


@require_http_methods(["POST"])
def run_single_api(request, topic_id):
    """Trigger processing for a single topic."""
    try:
        topic = Topic.objects.get(id=topic_id)
    except Topic.DoesNotExist:
        return JsonResponse({'error': 'Topic not found'}, status=404)

    answer_count = Answer.objects.filter(topic=topic).count()
    if answer_count == 0:
        return JsonResponse({'error': 'No answers to analyze'}, status=400)

    result, _ = Result.objects.get_or_create(topic=topic)
    result.status = 'running'
    result.save()

    try:
        proposed = discover_themes_only(topic)
        result.proposed_themes = proposed
        result.save()

        themes = run_classification_with_themes(topic, proposed)
        sentiment = {}
        if topic.analyze_sentiment:
            sentiment = run_sentiment_analysis(topic)
        summary = generate_summary(topic)

        result.themes = themes
        result.sentiment = sentiment
        result.summary = summary
        result.answer_count = answer_count
        result.analyzed_at = timezone.now()
        result.status = 'completed'
        result.save()

        return JsonResponse({
            'success': True,
            'topic_id': topic.id,
            'status': 'completed',
            'themes_count': len(themes),
        })
    except Exception as e:
        print(f"[error] topic {topic.id}: {e}")
        traceback.print_exc()
        result.status = 'failed'
        result.save()
        return JsonResponse({
            'success': False,
            'topic_id': topic.id,
            'status': 'failed',
            'error': str(e),
        }, status=500)



@require_http_methods(["GET"])
def get_answers_api(request, topic_id):
    """Return all answers for a topic (for the quote wall)."""
    try:
        topic = Topic.objects.get(id=topic_id)
    except Topic.DoesNotExist:
        return JsonResponse({'error': 'Topic not found'}, status=404)

    answers = list(Answer.objects.filter(topic=topic).values('id', 'text'))
    return JsonResponse({'answers': answers})


@require_http_methods(["POST"])
def discover_themes_api(request, topic_id):
    """Run Pass 1 (theme discovery) and save proposed_themes; set status='editing'."""
    try:
        topic = Topic.objects.get(id=topic_id)
    except Topic.DoesNotExist:
        return JsonResponse({'error': 'Topic not found'}, status=404)

    answer_count = Answer.objects.filter(topic=topic).count()
    if answer_count == 0:
        return JsonResponse({'error': 'No answers to analyze'}, status=400)

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}
    custom_prompt = body.get('custom_prompt', '') or ''

    result, _ = Result.objects.get_or_create(topic=topic)
    result.status = 'discovering'
    result.save()

    try:
        themes = discover_themes_only(topic, custom_prompt=custom_prompt or None)
        result.proposed_themes = themes
        result.status = 'editing'
        result.save()

        return JsonResponse({
            'success': True,
            'topic_id': topic.id,
            'status': 'editing',
            'proposed_themes': themes,
        })
    except Exception as e:
        print(f"[error] discover topic {topic.id}: {e}")
        traceback.print_exc()
        result.status = 'failed'
        result.save()
        return JsonResponse({
            'success': False,
            'topic_id': topic.id,
            'status': 'failed',
            'error': str(e),
        }, status=500)


@require_http_methods(["POST"])
def classify_with_themes_api(request, topic_id):
    """Run Pass 2 with user-edited themes; set status='completed'."""
    try:
        topic = Topic.objects.get(id=topic_id)
    except Topic.DoesNotExist:
        return JsonResponse({'error': 'Topic not found'}, status=404)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    themes_input = data.get('themes', [])
    if not themes_input:
        return JsonResponse({'error': 'themes is required'}, status=400)

    answer_count = Answer.objects.filter(topic=topic).count()
    result, _ = Result.objects.get_or_create(topic=topic)
    result.status = 'classifying'
    result.save()

    try:
        full_themes = run_classification_with_themes(topic, themes_input)

        sentiment = {}
        if topic.analyze_sentiment:
            sentiment = run_sentiment_analysis(topic)
        summary = generate_summary(topic)

        result.themes = full_themes
        result.proposed_themes = themes_input  # save the final user-edited set
        result.sentiment = sentiment
        result.summary = summary
        result.answer_count = answer_count
        result.analyzed_at = timezone.now()
        result.status = 'completed'
        result.save()

        return JsonResponse({
            'success': True,
            'topic_id': topic.id,
            'status': 'completed',
            'themes_count': len(full_themes),
        })
    except Exception as e:
        print(f"[error] classify topic {topic.id}: {e}")
        traceback.print_exc()
        result.status = 'failed'
        result.save()
        return JsonResponse({
            'success': False,
            'topic_id': topic.id,
            'status': 'failed',
            'error': str(e),
        }, status=500)


@require_http_methods(["GET"])
def get_all_results_api(request, interview_id):
    """Get results for all topics."""
    interview = get_object_or_404(Interview, uuid=interview_id)
    qs = Topic.objects.filter(interview=interview)
    topics = qs.select_related('result').prefetch_related('answer_set').order_by('order')

    all_results = []
    for topic in topics:
        result = getattr(topic, 'result', None)
        answers = {str(a.id): a.text for a in topic.answer_set.all()}

        if not result or result.status not in ('completed', 'classifying'):
            all_results.append({
                'topic_id': topic.id,
                'topic_text': topic.name,
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
            'topic_id': topic.id,
            'topic_text': topic.name,
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
def chat_api(request, interview_id):
    """Chat with all survey answers."""
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        chat_history = data.get('history', [])

        if not message:
            return JsonResponse({'error': 'message is required'}, status=400)

        interview = get_object_or_404(Interview, uuid=interview_id)
        response_text = chat_with_all_answers(message, chat_history, interview=interview)

        return JsonResponse({
            'success': True,
            'response': response_text
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
