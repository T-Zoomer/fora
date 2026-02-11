from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard_view, name='results_dashboard'),
    path('api/run-all/', views.run_all_api, name='run_all_results'),
    path('api/results/', views.get_all_results_api, name='get_all_results'),
    path('api/chat/', views.chat_api, name='results_chat'),
]
