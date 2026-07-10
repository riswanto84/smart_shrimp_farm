from django.contrib import admin
from .models import CultivationCycle


@admin.register(CultivationCycle)
class CultivationCycleAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'target_end_date', 'actual_end_date', 'status', 'target_duration_days')
    list_filter = ('status',)
    search_fields = ('name', 'notes')
