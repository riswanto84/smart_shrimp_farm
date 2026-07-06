from django.urls import path
from . import views
app_name = 'sales'
urlpatterns = [
    path('cashier/', views.cashier, name='cashier'),
    path('customers/', views.customers, name='customers'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('invoices/', views.invoices, name='invoices'),
    path('invoices/export/excel/', views.export_sales_excel, name='export_sales_excel'),
    path('invoices/export/pdf/', views.export_sales_pdf, name='export_sales_pdf'),
    path('invoice/<int:pk>/', views.invoice, name='invoice'),
    path('invoice/<int:pk>/edit/', views.edit_sale, name='edit_sale'),
    path('invoice/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
]
