from django.urls import path
from . import views
app_name = 'finance'
urlpatterns = [
    path('expenses/', views.expenses, name='expenses'),
    path('expenses/add/', views.add_expense, name='add_expense'),
    path('expenses/export/excel/', views.export_expenses_excel, name='export_expenses_excel'),
    path('expenses/export/pdf/', views.export_expenses_pdf, name='export_expenses_pdf'),
    path('profit-loss/', views.profit_loss, name='profit_loss'),
    path('profit-loss/export/excel/', views.export_profit_loss_excel, name='export_profit_loss_excel'),
    path('profit-loss/export/pdf/', views.export_profit_loss_pdf, name='export_profit_loss_pdf'),
]
