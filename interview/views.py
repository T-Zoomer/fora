import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .models import Topic, Answer, Respondent
from .interview_service import conduct_interview


def get_or_create_respondent(request):
    respondent_id = request.session.get('respondent_id')
    if respondent_id:
        try:
            return Respondent.objects.get(id=respondent_id)
        except Respondent.DoesNotExist:
            pass
    respondent = Respondent.objects.create()
    request.session['respondent_id'] = respondent.id
    return respondent


def interview_view(request):
    return render(request, 'interview/interview.html')


@require_http_methods(["GET"])
def interview_topics_api(request):
    topics = Topic.objects.all()
    return JsonResponse({
        'topics': [
            {'id': t.pk, 'name': t.name}
            for t in topics
        ],
    })


@require_http_methods(["POST"])
def interview_chat_api(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        chat_history = data.get('history', [])
        covered_topics = data.get('covered_topics', [])

        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)

        result = conduct_interview(user_message, chat_history, covered_topics)

        respondent = get_or_create_respondent(request)
        newly_covered = [t for t in result['covered_topics'] if t not in covered_topics]
        topic_responses = result.get('topic_responses', {})

        for topic_id in newly_covered:
            topic_obj = Topic.objects.get(pk=topic_id)
            answer_text = topic_responses.get(topic_id, user_message)
            Answer.objects.create(
                topic=topic_obj,
                respondent=respondent,
                text=answer_text
            )

        raw_answers = {topic_id: topic_responses.get(topic_id, user_message) for topic_id in newly_covered}

        return JsonResponse({
            'success': True,
            'response': result['response'],
            'covered_topics': result['covered_topics'],
            'raw_answers': raw_answers,
            'interview_complete': result['interview_complete'],
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
