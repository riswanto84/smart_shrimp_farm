from django.urls import path
from . import views
app_name = 'finance'
urlpatterns = [
    path('expenses/', views.expenses, name='expenses'), path('expenses/add/', views.add_expense, name='add_expense'),
    path('expenses/export/excel/', views.export_expenses_excel, name='export_expenses_excel'), path('expenses/export/pdf/', views.export_expenses_pdf, name='export_expenses_pdf'),
    path('expenses/<int:pk>/edit/', views.edit_expense, name='edit_expense'), path('expenses/<int:pk>/delete/', views.delete_expense, name='delete_expense'),
    path('profit-loss/', views.profit_loss, name='profit_loss'), path('profit-loss/export/excel/', views.export_profit_loss_excel, name='export_profit_loss_excel'), path('profit-loss/export/pdf/', views.export_profit_loss_pdf, name='export_profit_loss_pdf'),
    path('periodic-report/', views.periodic_report, name='periodic_report'), path('periodic-report/export/excel/', views.export_periodic_report_excel, name='export_periodic_report_excel'), path('periodic-report/export/pdf/', views.export_periodic_report_pdf, name='export_periodic_report_pdf'),
    path('tax/',views.tax_dashboard,name='tax_dashboard'),
    path('tax/gross-turnover/',views.gross_turnover,name='gross_turnover'), path('tax/gross-turnover/add/',views.add_other_revenue,name='add_other_revenue'), path('tax/gross-turnover/excel/',views.export_gross_turnover_excel,name='export_gross_turnover_excel'), path('tax/gross-turnover/pdf/',views.export_gross_turnover_pdf,name='export_gross_turnover_pdf'),
    path('tax/profit-loss/',views.tax_profit_loss,name='tax_profit_loss'), path('tax/profit-loss/pdf/',views.export_tax_profit_loss_pdf,name='export_tax_profit_loss_pdf'),
    path('tax/balance/entries/',views.balance_entries,name='balance_entries'), path('tax/balance/entries/add/',views.add_balance_entry,name='add_balance_entry'), path('tax/balance/',views.balance_sheet,name='balance_sheet'), path('tax/balance/pdf/',views.export_balance_sheet_pdf,name='export_balance_sheet_pdf'),
    path('tax/assets/',views.assets,name='assets'), path('tax/assets/add/',views.add_asset,name='add_asset'), path('tax/assets/<int:pk>/edit/',views.edit_asset,name='edit_asset'),
    path('tax/depreciation/',views.depreciation_report,name='depreciation'), path('tax/depreciation/pdf/',views.export_depreciation_pdf,name='export_depreciation_pdf'),
]
