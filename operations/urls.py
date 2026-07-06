from django.urls import path
from . import views
app_name = 'operations'
urlpatterns = [
    path('parameters/', views.parameters, name='parameters'),
    path('parameters/add/', views.add_parameter, name='add_parameter'),
    path('parameters/export/excel/', views.export_parameters_excel, name='export_parameters_excel'),
    path('parameters/export/pdf/', views.export_parameters_pdf, name='export_parameters_pdf'),
    path('harvests/', views.harvests, name='harvests'),
    path('harvests/add/', views.add_harvest, name='add_harvest'),
    path('harvests/export/excel/', views.export_harvests_excel, name='export_harvests_excel'),
    path('harvests/export/pdf/', views.export_harvests_pdf, name='export_harvests_pdf'),
]
