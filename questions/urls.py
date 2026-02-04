from django.urls import path

from . import views

urlpatterns = [
    path('', views.question_view, name='home'),
    path('question/<int:question_id>/', views.question_view, name='question'),
    path('question/<int:question_id>/submit/', views.submit_answer, name='submit_answer'),
    path('done/', views.done_view, name='done'),
    path('api/tts/<int:question_id>/', views.tts_view, name='tts'),
    path('api/transcribe/', views.transcribe_view, name='transcribe'),
    path('api/realtime-session/', views.realtime_session_view, name='realtime_session'),
    path('api/question/<int:question_id>/', views.question_api_view, name='question_api'),
    path('api/questions/', views.questions_api_view, name='questions_api'),
    path('api/submit-answer/', views.submit_answer_api, name='submit_answer_api'),
]
