from django.contrib import admin
from .models import CultivationCycle


@admin.register(CultivationCycle)
class CultivationCycleAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'status', 'target_doc', 'target_size', 'target_biomass_ton', 'target_fcr', 'target_sr_percent')
    list_filter = ('status',)
    search_fields = ('name', 'notes')
