from django.urls import path
from . import views

app_name = 'payroll'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/add/', views.employee_form, name='employee_add'),
    path('employees/<int:pk>/edit/', views.employee_form, name='employee_edit'),
    path('periods/', views.period_list, name='period_list'),
    path('periods/add/', views.period_form, name='period_add'),
    path('periods/<int:pk>/edit/', views.period_form, name='period_edit'),
    path('periods/<int:pk>/', views.period_detail, name='period_detail'),
    path('periods/<int:period_pk>/records/add/', views.record_form, name='record_add'),
    path('records/<int:pk>/edit/', views.record_form, name='record_edit'),
    path('records/<int:pk>/delete/', views.record_delete, name='record_delete'),
    path('records/<int:pk>/slip/', views.salary_slip, name='salary_slip'),
    path('reports/', views.report, name='report'),
    path('reports/excel/', views.report_excel, name='report_excel'),
]
