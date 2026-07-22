from django.urls import path
from . import views
app_name = 'sales'
urlpatterns = [
    path('dashboard/', views.sales_dashboard, name='dashboard'),
    path('cashier/', views.cashier, name='cashier'),
    path('customers/', views.customers, name='customers'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('invoices/', views.invoices, name='invoices'),
    path('invoices/export/excel/', views.export_sales_excel, name='export_sales_excel'),
    path('invoices/export/pdf/', views.export_sales_pdf, name='export_sales_pdf'),
    path('invoice/<int:pk>/', views.invoice, name='invoice'),
    path('invoice/<int:pk>/edit/', views.edit_sale, name='edit_sale'),
    path('invoice/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('documents/<int:pk>/delete/', views.delete_sale_document, name='delete_sale_document'),
    path('invoice/<int:pk>/midtrans/create/', views.create_midtrans_payment, name='create_midtrans_payment'),
    path('invoice/<int:pk>/midtrans/check/', views.check_midtrans_payment, name='check_midtrans_payment'),
    path('midtrans/notification/', views.midtrans_notification, name='midtrans_notification'),
    path('customers/<int:pk>/edit/', views.edit_customer, name='edit_customer'),
    path('customers/<int:pk>/delete/', views.delete_customer, name='delete_customer'),
]
