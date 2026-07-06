from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
from ponds.models import Pond
from operations.models import DailyParameter, Harvest, Treatment, FeedLog
from sales.models import Customer, Sale, SaleItem
from finance.models import OperationalExpense
from accounts.models import Role, PermissionItem, AuditLog

class Command(BaseCommand):
    help='Isi data dummy SMART SHRIMP FARM untuk demo awal'
    def handle(self,*args,**opts):
        roles=[('Owner','Akses penuh owner'),('Admin','Kelola data operasional dan laporan'),('Teknisi','Input parameter, pakan, treatment'),('Kasir','Input penjualan dan nota'),('Investor','Lihat dashboard investor read only'),('Akuntan','Kelola keuangan')]
        role_objs={}
        for name,desc in roles:
            role_objs[name],_=Role.objects.get_or_create(name=name, defaults={'description':desc})
        perms=['dashboard.view','kolam.view','kolam.add','kolam.edit','parameter.view','parameter.add','panen.view','panen.add','sales.view','sales.add','finance.view','finance.add','investor.view','laporan.export','users.manage']
        for code in perms:
            PermissionItem.objects.get_or_create(code=code, defaults={'name':code.replace('.',' ').title(),'group':code.split('.')[0]})
        admin,created=User.objects.get_or_create(username='riswanto', defaults={'email':'riswanto@udangemasnusantara.com','first_name':'Riswanto'})
        if created: admin.set_password('admin12345'); admin.is_staff=True; admin.is_superuser=True; admin.save()
        admin.userprofile.roles.set([role_objs['Owner'],role_objs['Admin']])
        data=[('K-01','Kolam 1',1848,'Persiapan'),('K-02','Kolam 2',1848,'Budidaya'),('K-03','Kolam 3',1848,'Budidaya'),('K-04','Kolam 4',1848,'Budidaya'),('K-05','Kolam 5',1848,'Panen'),('K-06','Kolam 6',1707,'Persiapan')]
        ponds=[]
        for code,name,area,status in data:
            p,_=Pond.objects.update_or_create(code=code, defaults={'name':name,'area_m2':area,'depth_m':1.4,'capacity_seed':200000 if status=='Budidaya' else 0,'pond_type':'HDPE','status':status,'location':'Pantai Mekar, Muara Gembong','notes':'Data dummy awal aplikasi'})
            ponds.append(p)
        today=date(2026,6,21)
        DailyParameter.objects.all().delete(); Harvest.objects.all().delete(); Treatment.objects.all().delete(); FeedLog.objects.all().delete()
        for idx,p in enumerate(ponds, start=1):
            if p.status in ['Budidaya','Panen']:
                for d in range(7):
                    DailyParameter.objects.create(pond=p, technician=admin, date=today-timedelta(days=d), doc=45+d+idx, temperature=Decimal('28.4')+Decimal(idx)/10, ph_morning=Decimal('7.6'), ph_evening=Decimal('7.8')+Decimal(idx)/20, do_morning=Decimal('5.8'), do_night=Decimal('5.6'), salinity=Decimal('18'), alkalinity=Decimal('120'), transparency=Decimal('35'), feed_kg=Decimal('40')+idx, mortality=idx*2, water_color='Hijau kecoklatan', ai_recommendation='Kondisi kolam normal. Pertahankan aerasi malam dan pantau pH sore.')
                Treatment.objects.create(pond=p,date=today-timedelta(days=1),name='Probiotik EM4',dose='1 ppm',notes='Treatment rutin dummy')
                FeedLog.objects.create(pond=p,date=today,feed_name='Pelet 781-2',quantity_kg=Decimal('40')+idx)
        h1=Harvest.objects.create(pond=ponds[4],date=today-timedelta(days=1),harvest_type='Parsial',size_text='50',total_kg=Decimal('4100'),notes='Panen parsial dummy')
        h2=Harvest.objects.create(pond=ponds[2],date=today-timedelta(days=3),harvest_type='Parsial',size_text='40-50',total_kg=Decimal('1200'),notes='Panen parsial dummy')
        Customer.objects.all().delete(); Sale.objects.all().delete()
        c1=Customer.objects.create(name='PT Bahari Sentosa', phone='0812-1111-2222', email='purchasing@bahari.co.id', address='Jakarta')
        c2=Customer.objects.create(name='UD Samudra Jaya', phone='0813-3333-4444', email='samudra@example.com', address='Bekasi')
        for i,(c,h,kg,price) in enumerate([(c1,h1,120,70000),(c2,h2,80,72000),(c1,h1,250,69000)], start=1):
            s=Sale.objects.create(invoice_no=f'INV/2026/06/{i:04d}', customer=c, total_kg=kg, total_amount=kg*price, payment_method='Transfer', status='Lunas', cashier=admin, notes='Data dummy')
            SaleItem.objects.create(sale=s, harvest=h, size_text=h.size_text, weight_kg=kg, price_per_kg=price, subtotal=kg*price)
        OperationalExpense.objects.all().delete()
        expenses=[('Pakan','Pakan CP 30 sak',15000000,ponds[1]),('Listrik','Listrik PLN Mei 2026',3200000,None),('Tenaga Kerja','Gaji Teknisi Juni',5000000,None),('Obat & Probiotik','Probiotik EM4 10 liter',1250000,ponds[2]),('BBM','Solar Genset 200 liter',1800000,None)]
        for i,(cat,name,amount,pond) in enumerate(expenses):
            OperationalExpense.objects.create(date=today-timedelta(days=i),category=cat,name=name,amount=amount,pond=pond,payment_method='Transfer' if i<3 else 'Cash',notes='Data dummy pengeluaran')
        for uname,roleset in [('budi',['Teknisi','Kasir']),('ahmad',['Teknisi']),('investor.a',['Investor']),('akuntan',['Akuntan'])]:
            u,created=User.objects.get_or_create(username=uname, defaults={'email':uname+'@example.com','first_name':uname.title()})
            if created: u.set_password('12345678'); u.save()
            u.userprofile.roles.set([role_objs[r] for r in roleset])
        AuditLog.objects.all().delete()
        AuditLog.objects.create(user=admin, action='Data dummy SMART SHRIMP FARM dibuat')
        self.stdout.write(self.style.SUCCESS('Data dummy berhasil dibuat. Login: riswanto / admin12345'))
