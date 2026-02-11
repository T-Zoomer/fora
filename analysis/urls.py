from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard_view, name='analysis_dashboard'),
    path('api/questions/', views.questions_api, name='analysis_questions_api'),
    path('api/correlations/', views.correlation_api, name='correlation_api'),
]
