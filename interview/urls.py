from django.urls import path

from . import views

urlpatterns = [
    path('', views.interview_redirect_view, name='home'),
    path('<uuid:interview_id>/', views.interview_view, name='interview'),
    path('api/interview/<uuid:interview_id>/topics/', views.interview_topics_api, name='interview_topics'),
    path('api/interview/<uuid:interview_id>/opening/', views.interview_opening_api, name='interview_opening'),
    path('api/interview/<uuid:interview_id>/chat/', views.interview_chat_api, name='interview_chat'),
]
