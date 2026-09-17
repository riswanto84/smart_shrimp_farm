from django.urls import path
from . import views
app_name='weather_ai'
urlpatterns=[path('',views.forecast,name='forecast')]
