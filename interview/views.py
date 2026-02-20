import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import Topic, Answer, Respondent, Interview
from .interview_service import conduct_interview, generate_opening_question


def interview_redirect_view(request):
    interview = Interview.objects.order_by('created_at').first()
    if interview is None:
        from django.http import Http404
        raise Http404
    return redirect(f'/{interview.uuid}/')


def get_or_create_respondent(request, interview):
    session_key = f'respondent_id_{interview.id}'
    respondent_id = request.session.get(session_key)
    if respondent_id:
        try:
            return Respondent.objects.get(id=respondent_id)
        except Respondent.DoesNotExist:
            pass
    respondent = Respondent.objects.create(interview=interview)
    request.session[session_key] = respondent.id
    return respondent


def interview_view(request, interview_id):
    interview = get_object_or_404(Interview, uuid=interview_id)
    return render(request, 'interview/interview.html', {'interview': interview})


@require_http_methods(["GET"])
def interview_topics_api(request, interview_id):
    interview = get_object_or_404(Interview, uuid=interview_id)
    topics = Topic.objects.filter(interview=interview)
    return JsonResponse({
        'topics': [
            {'id': t.pk, 'name': t.name}
            for t in topics
        ],
        'intro_message': interview.intro_message,
    })


@require_http_methods(["GET"])
def interview_opening_api(request, interview_id):
    interview = get_object_or_404(Interview, uuid=interview_id)
    topics = list(Topic.objects.filter(interview=interview))
    question = generate_opening_question(topics)
    return JsonResponse({'question': question})


@require_http_methods(["POST"])
def interview_chat_api(request, interview_id):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        chat_history = data.get('history', [])
        covered_topics = data.get('covered_topics', [])

        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)

        interview = get_object_or_404(Interview, uuid=interview_id)
        result = conduct_interview(user_message, chat_history, covered_topics, interview=interview)

        respondent = get_or_create_respondent(request, interview=interview)
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
