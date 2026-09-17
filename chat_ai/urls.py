from django.urls import path
from . import views, ai_views

app_name = 'chat_ai'
urlpatterns = [
    path('', views.chat, name='chat'),
    path('api/sessions/new/', views.new_session, name='new_session'),
    path('api/sessions/<int:session_id>/messages/', views.session_messages, name='session_messages'),
    path('api/sessions/<int:session_id>/delete/', views.delete_session, name='delete_session'),
    path('api/sessions/<int:session_id>/rename/', views.rename_session, name='rename_session'),
    path('api/stream/', views.stream_chat, name='stream_chat'),
    path('session/<int:session_id>/important/', views.mark_important, name='mark_important'),
    path('session/<int:session_id>/normal/', views.unmark_important, name='unmark_important'),
    path('pond-analysis/', ai_views.ai_pond_analysis, name='ai_pond_analysis'),
    path('feed-recommendation/', ai_views.ai_feed_recommendation, name='ai_feed_recommendation'),
    path('siphon-warning/', ai_views.ai_siphon_warning, name='ai_siphon_warning'),
    path('harvest-prediction/', ai_views.ai_harvest_prediction, name='ai_harvest_prediction'),
    path('daily-summary/', ai_views.ai_daily_summary, name='ai_daily_summary'),
]
