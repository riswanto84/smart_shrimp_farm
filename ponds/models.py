from django.db import models
class Pond(models.Model):
    STATUS=[('Persiapan','Persiapan'),('Budidaya','Budidaya'),('Panen','Panen'),('Kosong','Kosong'),('Perbaikan','Perbaikan')]
    code=models.CharField(max_length=20, unique=True)
    name=models.CharField(max_length=100)
    area_m2=models.DecimalField(max_digits=10, decimal_places=2, default=0)
    depth_m=models.DecimalField(max_digits=5, decimal_places=2, default=0)
    capacity_seed=models.IntegerField(default=0)
    pond_type=models.CharField(max_length=80, blank=True)
    status=models.CharField(max_length=20, choices=STATUS, default='Persiapan')
    location=models.CharField(max_length=150, blank=True)
    photo=models.ImageField(upload_to='ponds/', blank=True, null=True)
    notes=models.TextField(blank=True)
    def __str__(self): return self.name
