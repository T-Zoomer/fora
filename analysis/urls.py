from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard_view, name='analysis_dashboard'),
    path('api/run-all/', views.run_all_analysis_api, name='run_all_analysis'),
    path('api/results/', views.get_all_results_api, name='get_all_results'),
]
