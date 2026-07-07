from django.urls import path
from . import views
from . import ai_views
app_name='chat_ai'
urlpatterns=[
    path('', views.chat, name='chat'),
    path('pond-analysis/', ai_views.ai_pond_analysis, name='ai_pond_analysis'),
    path('feed-recommendation/', ai_views.ai_feed_recommendation, name='ai_feed_recommendation'),
    path('siphon-warning/', ai_views.ai_siphon_warning, name='ai_siphon_warning'),
    path('harvest-prediction/', ai_views.ai_harvest_prediction, name='ai_harvest_prediction'),
    path('daily-summary/', ai_views.ai_daily_summary, name='ai_daily_summary'),
]
