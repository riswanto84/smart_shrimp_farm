# Verifikasi Neraca Aset Biologis

Setelah deploy jalankan:

```bash
python manage.py check
python manage.py shell -c "from operations.models import Harvest; print(list(Harvest.objects.filter(pond__code__icontains='7').values('pond__code','pond__name','date','harvest_type','cycle__name')))"
```

Kolam dengan `harvest_type` Total/Final/Panen Total/Panen Final/Selesai tidak ditampilkan pada Aset Biologis. Siklus berstatus selesai dan kolam selain Budidaya/Panen juga dikeluarkan.
