import hashlib
import tempfile
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from openai import OpenAI

from .models import Question, Answer

# Cache directory for TTS audio files
TTS_CACHE_DIR = Path(tempfile.gettempdir()) / 'fora_tts_cache'
TTS_CACHE_DIR.mkdir(exist_ok=True)


def question_view(request, question_id=None):
    questions = Question.objects.all()

    if not questions.exists():
        return render(request, 'questions/no_questions.html')

    if question_id is None:
        question = questions.first()
    else:
        question = get_object_or_404(Question, id=question_id)

    question_list = list(questions)
    current_index = question_list.index(question)
    total = len(question_list)

    return render(request, 'questions/question.html', {
        'question': question,
        'current': current_index + 1,
        'total': total,
    })


@require_http_methods(["POST"])
def submit_answer(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    answer_text = request.POST.get('answer', '').strip()

    if answer_text:
        Answer.objects.create(question=question, text=answer_text)

    next_question = Question.objects.filter(order__gt=question.order).first()

    if next_question:
        return redirect('question', question_id=next_question.id)
    else:
        return redirect('done')


def done_view(request):
    return render(request, 'questions/done.html')


def question_api_view(request, question_id):
    """Return question data as JSON for voice mode."""
    question = get_object_or_404(Question, id=question_id)
    questions = Question.objects.all()
    question_list = list(questions)
    current_index = question_list.index(question)
    total = len(question_list)

    next_question = Question.objects.filter(order__gt=question.order).first()

    return JsonResponse({
        'id': question.id,
        'text': question.text,
        'current': current_index + 1,
        'total': total,
        'next_question_id': next_question.id if next_question else None,
    })


def questions_api_view(request):
    """Return all questions as JSON for single-page app."""
    questions = Question.objects.all().order_by('order')
    return JsonResponse({
        'questions': [
            {'id': q.id, 'text': q.text}
            for q in questions
        ]
    })


@require_http_methods(["POST"])
def submit_answer_api(request):
    """Submit an answer via JSON API."""
    import json
    try:
        data = json.loads(request.body)
        question_id = data.get('question_id')
        answer_text = data.get('answer', '').strip()

        if question_id and answer_text:
            question = get_object_or_404(Question, id=question_id)
            Answer.objects.create(question=question, text=answer_text)
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'Missing data'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)


def tts_view(request, question_id):
    """Generate TTS audio for a question using OpenAI's TTS API."""
    question = get_object_or_404(Question, id=question_id)

    # Create cache key based on question text
    cache_key = hashlib.md5(question.text.encode()).hexdigest()
    cache_file = TTS_CACHE_DIR / f'{cache_key}.mp3'

    # Return cached audio if available
    if cache_file.exists():
        return FileResponse(open(cache_file, 'rb'), content_type='audio/mpeg')

    # Generate TTS audio
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.audio.speech.create(
        model='tts-1',
        voice='alloy',
        input=question.text,
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
