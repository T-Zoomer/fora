def interview_context(request):
    from .models import Interview
    interviews = list(Interview.objects.order_by('created_at'))
    return {'interviews': interviews}
