from django.contrib import admin
from .models import Customer,Sale,SaleItem,SaleDocument
admin.site.register(Customer); admin.site.register(Sale); admin.site.register(SaleItem); admin.site.register(SaleDocument)
