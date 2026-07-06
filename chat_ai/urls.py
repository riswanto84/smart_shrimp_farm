from django.urls import path
from . import views
app_name='chat_ai'
urlpatterns=[path('',views.chat,name='chat')]
