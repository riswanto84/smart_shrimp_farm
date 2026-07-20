from django.contrib import admin
from .models import OperationalExpense, OtherRevenue, BalanceEntry, FixedAsset

@admin.register(OperationalExpense)
class OperationalExpenseAdmin(admin.ModelAdmin):
    list_display=('date','category','name','amount','is_fiscal_deductible')
    list_filter=('category','is_fiscal_deductible','date')

@admin.register(OtherRevenue)
class OtherRevenueAdmin(admin.ModelAdmin):
    list_display=('date','revenue_type','description','gross_amount')
    list_filter=('revenue_type','date')

@admin.register(BalanceEntry)
class BalanceEntryAdmin(admin.ModelAdmin):
    list_display=('as_of_date','account_type','group','account_name','amount')
    list_filter=('account_type','group','as_of_date')

@admin.register(FixedAsset)
class FixedAssetAdmin(admin.ModelAdmin):
    list_display=('code','name','category','use_date','total_cost','fiscal_group','status')
    list_filter=('category','fiscal_group','status')
