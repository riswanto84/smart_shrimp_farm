from django.contrib import admin
from .models import OperationalExpense, OtherRevenue, BalanceEntry, FixedAsset, TradeAccount, TradePayment, TradeDocument

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


class TradePaymentInline(admin.TabularInline):
    model = TradePayment
    extra = 0

@admin.register(TradeAccount)
class TradeAccountAdmin(admin.ModelAdmin):
    list_display=('account_type','transaction_date','due_date','partner_name','document_number','original_amount','payment_status')
    list_filter=('account_type','transaction_date','due_date')
    search_fields=('partner_name','document_number','description')
    inlines=(TradePaymentInline,)

@admin.register(TradePayment)
class TradePaymentAdmin(admin.ModelAdmin):
    list_display=('trade_account','payment_date','amount','payment_method','document_number')
    list_filter=('payment_method','payment_date')


@admin.register(TradeDocument)
class TradeDocumentAdmin(admin.ModelAdmin):
    list_display=('original_name','trade_account','payment','uploaded_by','uploaded_at')
    list_filter=('uploaded_at',)
    search_fields=('original_name','description','trade_account__partner_name','trade_account__document_number')
