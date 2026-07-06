from django.db import models
from django.contrib.auth.models import User
from ponds.models import Pond
class Stocking(models.Model):
    pond=models.ForeignKey(Pond,on_delete=models.CASCADE)
    date=models.DateField()
    seed_count=models.IntegerField()
    hatchery=models.CharField(max_length=100, blank=True)
    notes=models.TextField(blank=True)
class DailyParameter(models.Model):
    pond=models.ForeignKey(Pond,on_delete=models.CASCADE)
    technician=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True)
    date=models.DateField()
    doc=models.IntegerField(default=0)
    temperature=models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ph_morning=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    ph_evening=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    do_morning=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    do_night=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    salinity=models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    alkalinity=models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    transparency=models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    feed_kg=models.DecimalField(max_digits=8, decimal_places=2, default=0)
    mortality=models.IntegerField(default=0)
    water_color=models.CharField(max_length=80, blank=True)
    notes=models.TextField(blank=True)
    ai_recommendation=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
class Treatment(models.Model):
    pond=models.ForeignKey(Pond,on_delete=models.CASCADE); date=models.DateField(); name=models.CharField(max_length=120); dose=models.CharField(max_length=80,blank=True); notes=models.TextField(blank=True)
class FeedLog(models.Model):
    pond=models.ForeignKey(Pond,on_delete=models.CASCADE); date=models.DateField(); feed_name=models.CharField(max_length=100); quantity_kg=models.DecimalField(max_digits=8, decimal_places=2)
class Harvest(models.Model):
    pond=models.ForeignKey(Pond,on_delete=models.CASCADE); date=models.DateField(); harvest_type=models.CharField(max_length=30, default='Parsial'); size_text=models.CharField(max_length=50); total_kg=models.DecimalField(max_digits=10, decimal_places=2); notes=models.TextField(blank=True)
