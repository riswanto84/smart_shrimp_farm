from django.urls import path
from . import views
urlpatterns=[path('',views.home,name='home'),path('dashboard/',views.dashboard,name='dashboard'),path('notifications/read/',views.mark_notifications_read,name='notifications_read'),path('ollama/status/',views.ollama_status_api,name='ollama_status_api')]
