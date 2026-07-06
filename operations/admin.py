from django.contrib import admin
from .models import Stocking,DailyParameter,Treatment,FeedLog,Harvest
admin.site.register(Stocking); admin.site.register(DailyParameter); admin.site.register(Treatment); admin.site.register(FeedLog); admin.site.register(Harvest)
