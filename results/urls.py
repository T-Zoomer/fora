from django.urls import path

from . import views

urlpatterns = [
    path('', views.results_redirect_view, name='results_home'),
    path('<uuid:interview_id>/', views.dashboard_view, name='results_dashboard'),
    path('<uuid:interview_id>/api/results/', views.get_all_results_api, name='get_all_results'),
    path('<uuid:interview_id>/api/chat/', views.chat_api, name='results_chat'),
    path('<uuid:interview_id>/api/close/', views.close_interview_api, name='close_interview'),
    path('<uuid:interview_id>/api/interview-sessions/', views.sessions_api, name='sessions'),
    path('api/run/<int:topic_id>/', views.run_single_api, name='run_single_result'),
    path('api/discover/<int:topic_id>/', views.discover_themes_api, name='discover_themes'),
    path('api/classify/<int:topic_id>/', views.classify_with_themes_api, name='classify_with_themes'),
    path('api/answers/<int:topic_id>/', views.get_answers_api, name='get_answers'),
]
