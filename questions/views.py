import hashlib
import json
import tempfile
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from openai import OpenAI

from .models import Interview, Answer, Respondent
from .interview_service import conduct_interview, get_opening_message, get_topics_status, INTERVIEW_TOPICS

# Cache directory for TTS audio files
TTS_CACHE_DIR = Path(tempfile.gettempdir()) / 'fora_tts_cache'
TTS_CACHE_DIR.mkdir(exist_ok=True)


def get_or_create_respondent(request):
    """Get existing respondent from session or create a new one."""
    respondent_id = request.session.get('respondent_id')
    if respondent_id:
        try:
            return Respondent.objects.get(id=respondent_id)
        except Respondent.DoesNotExist:
            pass
    respondent = Respondent.objects.create()
    request.session['respondent_id'] = respondent.id
    return respondent


def interview_detail_view(request, interview_id=None):
    interviews = Interview.objects.all()

    if not interviews.exists():
        return render(request, 'questions/no_questions.html')

    if interview_id is None:
        interview = interviews.first()
    else:
        interview = get_object_or_404(Interview, id=interview_id)

    interview_list = list(interviews)
    current_index = interview_list.index(interview)
    total = len(interview_list)

    return render(request, 'questions/question.html', {
        'interview': interview,
        'current': current_index + 1,
        'total': total,
    })


@require_http_methods(["POST"])
def submit_answer(request, interview_id):
    interview = get_object_or_404(Interview, id=interview_id)
    answer_text = request.POST.get('answer', '').strip()

    if answer_text:
        respondent = get_or_create_respondent(request)
        Answer.objects.create(interview=interview, text=answer_text, respondent=respondent)

    next_interview = Interview.objects.filter(order__gt=interview.order).first()

    if next_interview:
        return redirect('interview_detail', interview_id=next_interview.id)
    else:
        return redirect('done')


def done_view(request):
    return render(request, 'questions/done.html')


def interview_api_view(request, interview_id):
    """Return interview data as JSON for voice mode."""
    interview = get_object_or_404(Interview, id=interview_id)
    interviews = Interview.objects.all()
    interview_list = list(interviews)
    current_index = interview_list.index(interview)
    total = len(interview_list)

    next_interview = Interview.objects.filter(order__gt=interview.order).first()

    return JsonResponse({
        'id': interview.id,
        'text': interview.text,
        'current': current_index + 1,
        'total': total,
        'next_interview_id': next_interview.id if next_interview else None,
    })


def interviews_api_view(request):
    """Return all interviews as JSON for single-page app."""
    interviews = Interview.objects.all().order_by('order')
    return JsonResponse({
        'interviews': [
            {'id': i.id, 'text': i.text}
            for i in interviews
        ]
    })


@require_http_methods(["POST"])
def submit_answer_api(request):
    """Submit an answer via JSON API."""
    import json
    try:
        data = json.loads(request.body)
        interview_id = data.get('interview_id')
        answer_text = data.get('answer', '').strip()

        if interview_id and answer_text:
            interview = get_object_or_404(Interview, id=interview_id)
            respondent = get_or_create_respondent(request)
            Answer.objects.create(interview=interview, text=answer_text, respondent=respondent)
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'Missing data'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)


def tts_view(request, interview_id):
    """Generate TTS audio for an interview using OpenAI's TTS API."""
    interview = get_object_or_404(Interview, id=interview_id)

    # Create cache key based on interview text
    cache_key = hashlib.md5(interview.text.encode()).hexdigest()
    cache_file = TTS_CACHE_DIR / f'{cache_key}.mp3'

    # Return cached audio if available
    if cache_file.exists():
        return FileResponse(open(cache_file, 'rb'), content_type='audio/mpeg')

    # Generate TTS audio
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.audio.speech.create(
        model='tts-1',
        voice='alloy',
        input=interview.text,
    )

    # Save to cache
    response.stream_to_file(str(cache_file))

    return FileResponse(open(cache_file, 'rb'), content_type='audio/mpeg')


@require_http_methods(["POST"])
def transcribe_view(request):
    """Transcribe audio using OpenAI's Whisper API."""
    audio_file = request.FILES.get('audio')

    if not audio_file:
        return JsonResponse({'error': 'No audio file provided'}, status=400)

    # Save uploaded audio to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as tmp:
        for chunk in audio_file.chunks():
            tmp.write(chunk)
        tmp_path = tmp.name

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        with open(tmp_path, 'rb') as audio:
            transcript = client.audio.transcriptions.create(
                model='whisper-1',
                file=audio,
            )
        return JsonResponse({'text': transcript.text})
    finally:
        # Clean up temporary file
        Path(tmp_path).unlink(missing_ok=True)


def realtime_session_view(request):
    """Create an ephemeral token for OpenAI Realtime API."""
    import requests

    response = requests.post(
        'https://api.openai.com/v1/realtime/sessions',
        headers={
            'Authorization': f'Bearer {settings.OPENAI_API_KEY}',
            'Content-Type': 'application/json',
        },
        json={
            'model': 'gpt-4o-realtime-preview-2024-12-17',
            'modalities': ['text'],
            'input_audio_transcription': {
                'model': 'whisper-1',
            },
        },
    )

    if response.status_code == 200:
        return JsonResponse(response.json())
    else:
        return JsonResponse({'error': response.text}, status=response.status_code)


def interview_view(request):
    """Main interview page - chat-only mode."""
    return render(request, 'questions/interview.html')


def interview_topics_api(request):
    """Return interview topics configuration."""
    return JsonResponse({
        'topics': [
            {'id': t['id'], 'name': t['name']}
            for t in INTERVIEW_TOPICS
        ],
        'opening_message': get_opening_message()
    })


@require_http_methods(["POST"])
def interview_chat_api(request):
    """Handle interview chat messages using two-AI approach."""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        chat_history = data.get('history', [])
        covered_topics = data.get('covered_topics', [])

        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)

        result = conduct_interview(user_message, chat_history, covered_topics)

        # Store user responses for newly covered topics
        respondent = get_or_create_respondent(request)
        newly_covered = [t for t in result['covered_topics'] if t not in covered_topics]
        topic_responses = result.get('topic_responses', {})

        for topic_id in newly_covered:
            # Use the AI-extracted response for this topic, fallback to user_message
            answer_text = topic_responses.get(topic_id, user_message)

            # Find or create an interview for this topic
            topic = next(t for t in INTERVIEW_TOPICS if t['id'] == topic_id)
            interview_obj, _ = Interview.objects.get_or_create(
                text=topic['name'],
                defaults={'order': INTERVIEW_TOPICS.index(topic)}
            )
            Answer.objects.create(
                interview=interview_obj,
                respondent=respondent,
                text=answer_text
            )

        # Build answers dict for frontend
        raw_answers = {topic_id: topic_responses.get(topic_id, user_message) for topic_id in newly_covered}

        return JsonResponse({
            'success': True,
            'response': result['response'],
            'covered_topics': result['covered_topics'],
            'raw_answers': raw_answers,
            'interview_complete': result['interview_complete'],
            'analysis': result.get('analysis', {})  # Include analysis for debugging
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
