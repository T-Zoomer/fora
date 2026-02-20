from django.urls import path

from . import views

urlpatterns = [
    path('', views.interview_view, name='home'),
    path('api/interview/topics/', views.interview_topics_api, name='interview_topics'),
    path('api/interview/chat/', views.interview_chat_api, name='interview_chat'),
]
