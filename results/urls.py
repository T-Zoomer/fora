from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard_view, name='results_dashboard'),
    path('api/run/<int:interview_id>/', views.run_single_api, name='run_single_result'),
    path('api/discover/<int:interview_id>/', views.discover_themes_api, name='discover_themes'),
    path('api/classify/<int:interview_id>/', views.classify_with_themes_api, name='classify_with_themes'),
    path('api/answers/<int:interview_id>/', views.get_answers_api, name='get_answers'),
    path('api/results/', views.get_all_results_api, name='get_all_results'),
    path('api/chat/', views.chat_api, name='results_chat'),
]
