from django.urls import path
from . import views

app_name = 'cultivation'
urlpatterns = [
    path('', views.cycle_list, name='list'),
    path('add/', views.cycle_form, name='add'),
    path('<int:pk>/edit/', views.cycle_form, name='edit'),
    path('select/', views.select_cycle, name='select'),
]
