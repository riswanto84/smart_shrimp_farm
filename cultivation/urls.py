from django.urls import path
from . import views

app_name = 'cultivation'
urlpatterns = [
    path('', views.cycle_list, name='list'),
    path('add/', views.cycle_form, name='add'),
    path('<int:pk>/edit/', views.cycle_form, name='edit'),
    path('<int:pk>/report.pdf', views.cycle_report_pdf, name='report_pdf'),
    path('<int:pk>/close-and-next/', views.close_and_create_next_cycle, name='close_and_next'),
    path('history/', views.cycle_history, name='history'),
    path('history/<int:pk>/', views.cycle_history_detail, name='history_detail'),
    path('history/<int:pk>/excel/', views.cycle_history_excel, name='history_excel'),
    path('history/<int:pk>/pdf/', views.cycle_history_pdf, name='history_pdf'),
    path('select/', views.select_cycle, name='select'),
]
