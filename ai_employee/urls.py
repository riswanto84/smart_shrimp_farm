from django.urls import path
from . import views

app_name = 'ai_employee'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('operational-expense/', views.operational_expense, name='operational_expense'),
    path('operational-expense/<int:pk>/edit/', views.operational_expense_edit, name='operational_expense_edit'),
    path('api/chat/', views.chat, name='chat'),
    path('action/<int:pk>/approve/', views.approve, name='approve'),
    path('action/<int:pk>/reject/', views.reject, name='reject'),
]
