from django.urls import path

from . import views

urlpatterns = [
    # Interview (main)
    path('', views.interview_view, name='home'),
    path('done/', views.done_view, name='done'),

    # Interview API
    path('api/interview/topics/', views.interview_topics_api, name='interview_topics'),
    path('api/interview/chat/', views.interview_chat_api, name='interview_chat'),

    # Interview detail endpoints
    path('interview/<int:interview_id>/', views.interview_detail_view, name='interview_detail'),
    path('interview/<int:interview_id>/submit/', views.submit_answer, name='submit_answer'),
    path('api/tts/<int:interview_id>/', views.tts_view, name='tts'),
    path('api/transcribe/', views.transcribe_view, name='transcribe'),
    path('api/realtime-session/', views.realtime_session_view, name='realtime_session'),
    path('api/interview/<int:interview_id>/', views.interview_api_view, name='interview_api'),
    path('api/interviews/', views.interviews_api_view, name='interviews_api'),
    path('api/submit-answer/', views.submit_answer_api, name='submit_answer_api'),
]
