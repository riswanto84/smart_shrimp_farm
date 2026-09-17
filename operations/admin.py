from django.contrib import admin
from .models import (
    Stocking, DailyParameter, Treatment, FeedLog, Harvest,
    DailyPondRecord, AncoCheck, SamplingRecord, SiphonRecord,
)

@admin.register(Stocking)
class StockingAdmin(admin.ModelAdmin):
    list_display = ('date', 'pond', 'seed_count', 'hatchery')
    list_filter = ('date', 'pond')
    search_fields = ('pond__name', 'hatchery')

@admin.register(DailyPondRecord)
class DailyPondRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'pond', 'doc', 'feed_code', 'daily_feed_kg', 'weather', 'technician')
    list_filter = ('date', 'pond', 'weather')
    search_fields = ('pond__name', 'feed_code', 'treatment', 'notes')

@admin.register(AncoCheck)
class AncoCheckAdmin(admin.ModelAdmin):
    list_display = ('date', 'pond', 'doc', 'appetite_status', 'technician')
    list_filter = ('date', 'pond', 'appetite_status')

@admin.register(SamplingRecord)
class SamplingRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'pond', 'doc', 'sample_weight_g', 'sample_count', 'abw_g', 'size', 'adg_weekly', 'estimated_sr', 'biomass_kg', 'fcr', 'population', 'cumulative_feed_kg')
    list_filter = ('date', 'pond')
    search_fields = ('pond__name', 'harvest_estimation')

@admin.register(SiphonRecord)
class SiphonRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'pond', 'doc', 'dead_count', 'live_count', 'daily_total', 'accumulated_total', 'health_indicator')
    list_filter = ('date', 'pond', 'health_indicator')

admin.site.register(DailyParameter)
admin.site.register(Treatment)
admin.site.register(FeedLog)
admin.site.register(Harvest)
