from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from questions.models import Question, Answer
from .models import AnalysisResult
from .services import run_thematic_coding, run_sentiment_analysis


def dashboard_view(request):
    """Main analysis dashboard."""
    questions = Question.objects.all()
    total_answers = Answer.objects.count()
    analyzed_count = AnalysisResult.objects.filter(status='completed').count()

    # Check if any analysis is running
    is_running = AnalysisResult.objects.filter(status='running').exists()

    return render(request, 'analysis/dashboard.html', {
        'questions_count': questions.count(),
        'total_answers': total_answers,
        'analyzed_count': analyzed_count,
        'is_running': is_running,
    })


@require_http_methods(["POST"])
def run_all_analysis_api(request):
    """Trigger analysis for all questions."""
    questions = Question.objects.all()

    results = []
    for question in questions:
        # Skip questions with no answers
        answer_count = Answer.objects.filter(question=question).count()
        if answer_count == 0:
            continue

        # Get or create analysis result
        analysis, _ = AnalysisResult.objects.get_or_create(question=question)

        # Update status to running
        analysis.status = 'running'
        analysis.save()

        try:
            # Run thematic coding
            themes = run_thematic_coding(question)

            # Run sentiment analysis (if enabled for this question)
            sentiment = {}
            if question.analyze_sentiment:
                sentiment = run_sentiment_analysis(question)

            # Save results
            analysis.themes = themes
            analysis.sentiment = sentiment
            analysis.answer_count = answer_count
            analysis.status = 'completed'
            analysis.save()

            results.append({
                'question_id': question.id,
                'status': 'completed',
                'themes_count': len(themes),
                'sentiment_avg': sentiment.get('average'),
            })
        except Exception as e:
            analysis.status = 'failed'
            analysis.save()
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
    """Get analysis results for all questions."""
    questions = Question.objects.all().order_by('order')

    all_results = []
    for question in questions:
        analysis = AnalysisResult.objects.filter(question=question).first()
        answers = {str(a.id): a.text for a in Answer.objects.filter(question=question)}

        if not analysis or analysis.status != 'completed':
            all_results.append({
                'question_id': question.id,
                'question_text': question.text,
                'status': analysis.status if analysis else 'not_analyzed',
                'answer_count': len(answers),
                'themes': [],
            })
            continue

        # Enrich themes with answer texts
        themes_with_texts = []
        for theme in analysis.themes:
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
            'status': analysis.status,
            'analyzed_at': analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
            'answer_count': analysis.answer_count,
            'themes': themes_with_texts,
            'sentiment': analysis.sentiment,
        })

    return JsonResponse({'results': all_results})
