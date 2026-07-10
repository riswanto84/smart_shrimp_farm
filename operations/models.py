from decimal import Decimal, InvalidOperation
from datetime import timedelta, date as date_class, datetime as datetime_class

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.dateparse import parse_date
from ponds.models import Pond
from cultivation.models import CultivationCycle


def _date_value(value):
    """Pastikan DateField dari form (string YYYY-MM-DD) menjadi date object.
    Ini mencegah error saat field date dipakai untuk operasi tanggal seperti + timedelta.
    """
    if isinstance(value, datetime_class):
        return value.date()
    if isinstance(value, date_class):
        return value
    if isinstance(value, str):
        parsed = parse_date(value)
        if parsed:
            return parsed
    return timezone.localdate()


def _d(value, default='0'):
    try:
        if value in (None, ''):
            return Decimal(default)
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


class Stocking(models.Model):
    cycle = models.ForeignKey(CultivationCycle, on_delete=models.PROTECT, null=True, blank=True, related_name='%(class)s_records')
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE)
    date = models.DateField()
    seed_count = models.IntegerField()
    hatchery = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.pond} - {self.seed_count:,} ekor'.replace(',', '.')


class DailyParameter(models.Model):
    cycle = models.ForeignKey(CultivationCycle, on_delete=models.PROTECT, null=True, blank=True, related_name='%(class)s_records')
    pond=models.ForeignKey(Pond,on_delete=models.CASCADE)
    technician=models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True)
    WEATHER_CHOICES = [
        ('Cerah', 'Cerah'), ('Berawan', 'Berawan'), ('Hujan', 'Hujan'),
        ('Panas', 'Panas'), ('Angin Kencang', 'Angin Kencang'),
    ]
    date=models.DateField()
    doc=models.IntegerField(default=0)
    feed_code=models.CharField(max_length=80, blank=True)
    water_in_cm=models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    weather=models.CharField(max_length=30, choices=WEATHER_CHOICES, blank=True)
    water_level_cm=models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)  # kompatibilitas data lama
    water_level_morning_cm=models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    water_level_evening_cm=models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    temperature=models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ph_morning=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    ph_evening=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    do_morning=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    do_night=models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    salinity=models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    alkalinity=models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    transparency=models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)  # kompatibilitas data lama
    transparency_morning=models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    transparency_evening=models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    feed_kg=models.DecimalField(max_digits=8, decimal_places=2, default=0)
    mortality=models.IntegerField(default=0)
    water_color=models.CharField(max_length=80, blank=True)  # kompatibilitas data lama
    water_color_morning=models.CharField(max_length=80, blank=True)
    water_color_evening=models.CharField(max_length=80, blank=True)
    notes=models.TextField(blank=True)
    ai_recommendation=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

    @property
    def water_level_display(self):
        pagi = self.water_level_morning_cm if self.water_level_morning_cm is not None else self.water_level_cm
        sore = self.water_level_evening_cm if self.water_level_evening_cm is not None else self.water_level_cm
        return pagi, sore

    @property
    def transparency_display(self):
        pagi = self.transparency_morning if self.transparency_morning is not None else self.transparency
        sore = self.transparency_evening if self.transparency_evening is not None else self.transparency
        return pagi, sore


class Treatment(models.Model):
    cycle = models.ForeignKey(CultivationCycle, on_delete=models.PROTECT, null=True, blank=True, related_name='%(class)s_records')
    pond=models.ForeignKey(Pond,on_delete=models.CASCADE); date=models.DateField(); name=models.CharField(max_length=120); dose=models.CharField(max_length=80,blank=True); notes=models.TextField(blank=True)


class FeedLog(models.Model):
    cycle = models.ForeignKey(CultivationCycle, on_delete=models.PROTECT, null=True, blank=True, related_name='%(class)s_records')
    pond=models.ForeignKey(Pond,on_delete=models.CASCADE); date=models.DateField(); feed_name=models.CharField(max_length=100); quantity_kg=models.DecimalField(max_digits=8, decimal_places=2)


class Harvest(models.Model):
    cycle = models.ForeignKey(CultivationCycle, on_delete=models.PROTECT, null=True, blank=True, related_name='%(class)s_records')
    pond=models.ForeignKey(Pond,on_delete=models.CASCADE); date=models.DateField(); harvest_type=models.CharField(max_length=30, default='Parsial'); size_text=models.CharField(max_length=50); total_kg=models.DecimalField(max_digits=10, decimal_places=2); notes=models.TextField(blank=True)


class DailyPondRecord(models.Model):
    cycle = models.ForeignKey(CultivationCycle, on_delete=models.PROTECT, null=True, blank=True, related_name='%(class)s_records')
    WEATHER_CHOICES = [
        ('Cerah', 'Cerah'), ('Berawan', 'Berawan'), ('Hujan', 'Hujan'),
        ('Panas', 'Panas'), ('Angin Kencang', 'Angin Kencang'),
    ]
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='daily_records')
    technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(default=timezone.localdate)
    doc = models.PositiveIntegerField(default=0)
    feed_code = models.CharField(max_length=80, blank=True)
    daily_feed_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    water_in_cm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    weather = models.CharField(max_length=30, choices=WEATHER_CHOICES, blank=True)
    treatment = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'pond__name']
        unique_together = [('pond', 'date')]

    def __str__(self):
        return f'{self.date} - {self.pond} - DOC {self.doc}'


class AncoCheck(models.Model):
    cycle = models.ForeignKey(CultivationCycle, on_delete=models.PROTECT, null=True, blank=True, related_name='%(class)s_records')
    STATUS_CHOICES = [
        ('H', 'Habis'),
        ('S', 'Sisa'),
        ('SS', 'Sisa Sedikit'),
        ('-', 'Tidak Dicek'),
    ]
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='anco_checks')
    technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(default=timezone.localdate)
    doc = models.PositiveIntegerField(default=0)
    feed_code = models.CharField(max_length=80, blank=True)
    daily_feed_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # P/H pada format lapangan
    water_in_cm = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    weather = models.CharField(max_length=30, choices=DailyPondRecord.WEATHER_CHOICES, blank=True)
    treatment = models.TextField(blank=True)
    anco1_morning = models.CharField(max_length=2, choices=STATUS_CHOICES, default='-')
    anco2_morning = models.CharField(max_length=2, choices=STATUS_CHOICES, default='-')
    anco1_noon = models.CharField(max_length=2, choices=STATUS_CHOICES, default='-')
    anco2_noon = models.CharField(max_length=2, choices=STATUS_CHOICES, default='-')
    anco1_evening = models.CharField(max_length=2, choices=STATUS_CHOICES, default='-')
    anco2_evening = models.CharField(max_length=2, choices=STATUS_CHOICES, default='-')
    appetite_status = models.CharField(max_length=80, blank=True)
    recommendation = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'pond__name']
        unique_together = [('pond', 'date')]

    def save(self, *args, **kwargs):
        statuses = [self.anco1_morning, self.anco2_morning, self.anco1_noon, self.anco2_noon, self.anco1_evening, self.anco2_evening]
        ss = statuses.count('SS')
        s = statuses.count('S')
        h = statuses.count('H')
        if ss >= 2:
            self.appetite_status = 'Nafsu makan turun'
            self.recommendation = 'Kurangi pakan 15–25%, cek DO malam, pH, suhu, dan indikasi penyakit.'
        elif s >= 2:
            self.appetite_status = 'Ada sisa pakan'
            self.recommendation = 'Evaluasi pakan berikutnya, kurangi 5–10% jika tren berulang.'
        elif h >= 4:
            self.appetite_status = 'Nafsu makan baik'
            self.recommendation = 'Pakan dapat dipertahankan, kenaikan bertahap bila sampling mendukung.'
        else:
            self.appetite_status = 'Normal'
            self.recommendation = 'Pantau pola anco berikutnya.'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Cek Anco {self.pond} - {self.date}'


class SamplingRecord(models.Model):
    cycle = models.ForeignKey(CultivationCycle, on_delete=models.PROTECT, null=True, blank=True, related_name='%(class)s_records')
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='sampling_records')
    date = models.DateField(default=timezone.localdate)
    doc = models.PositiveIntegerField(default=0)

    # Kolom Excel: SHRIMP
    sample_weight_g = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='SHRIMP - Berat sampel total dalam gram')
    sample_count = models.PositiveIntegerField(default=0, help_text='SHRIMP - Jumlah sampel dalam ekor')

    # Kolom Excel: ABW, Size, ADG
    abw_last_g = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='ABW Last, otomatis dari sampling sebelumnya')
    abw_g = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='ABW Today = Berat / Jumlah')
    abw_target_g = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='ABW Target = ABW Last + Target ADG x interval hari')
    target_size = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='Target Size = 1000 / ABW Target')
    size = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='Size = 1000 / ABW Today')
    adg_weekly_target = models.DecimalField(max_digits=8, decimal_places=3, default=0, help_text='ADG Weekly Target')
    adg_weekly = models.DecimalField(max_digits=8, decimal_places=3, default=0, help_text='ADG Weekly Actual = (ABW Today - ABW Last) / interval hari')
    adg_cumulative = models.DecimalField(max_digits=8, decimal_places=3, default=0, help_text='ADG Accum = ABW Today / DOC')
    sampling_interval_days = models.PositiveIntegerField(default=0, help_text='Interval hari dari sampling sebelumnya')

    # Kolom Excel: Estimasi, Biomassa, FCR, Populasi
    estimated_sr = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='Estimasi SR% FR = Populasi FR / Tebar x 100')
    sr_index_percent = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='Estimasi SR% Index = Populasi Index / Tebar x 100')
    biomass_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text='Biomassa FR = F/D / FR x 100')
    biomass_index_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text='Biomassa Index = Populasi Index / Size')
    fcr = models.DecimalField(max_digits=8, decimal_places=3, default=0, help_text='FCR = Pakan Kumulatif / Biomassa FR')
    population = models.PositiveIntegerField(default=0, help_text='Populasi FR = Biomassa FR x Size')
    population_index = models.PositiveIntegerField(default=0, help_text='Populasi Index')

    # Kolom Excel: Pakan Kumulatif, Tebar, F/D, FR, Index
    cumulative_feed_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text='Pakan Kumulatif KG')
    stocking_count = models.PositiveIntegerField(default=0, help_text='Tebar')
    daily_feed_kg = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='F/D - Pakan harian')
    fr_percent = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text='FR%')
    index_score = models.DecimalField(max_digits=8, decimal_places=3, default=0, help_text='Index')

    harvest_estimation = models.CharField(max_length=160, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'pond__name']

    def save(self, *args, **kwargs):
        self.date = _date_value(self.date)

        weight = _d(self.sample_weight_g)
        count = self.sample_count or 0
        self.abw_g = (weight / Decimal(count)).quantize(Decimal('0.01')) if count else Decimal('0')
        self.size = (Decimal('1000') / _d(self.abw_g, '1')).quantize(Decimal('0.01')) if self.abw_g else Decimal('0')

        prev = SamplingRecord.objects.filter(pond=self.pond, date__lt=self.date).order_by('-date').first()
        if prev:
            self.abw_last_g = _d(prev.abw_g)
            self.sampling_interval_days = max((self.date - prev.date).days, 1)
        else:
            self.abw_last_g = Decimal('0')
            self.sampling_interval_days = 0

        days = Decimal(self.sampling_interval_days or 7)
        if self.abw_last_g and self.adg_weekly_target:
            self.abw_target_g = (_d(self.abw_last_g) + (_d(self.adg_weekly_target) * days)).quantize(Decimal('0.01'))
            self.target_size = (Decimal('1000') / _d(self.abw_target_g, '1')).quantize(Decimal('0.01')) if self.abw_target_g else Decimal('0')
        else:
            self.abw_target_g = Decimal('0')
            self.target_size = Decimal('0')

        if prev and self.abw_g:
            self.adg_weekly = ((_d(self.abw_g) - _d(self.abw_last_g)) / days).quantize(Decimal('0.001'))
        else:
            self.adg_weekly = Decimal('0')
        self.adg_cumulative = (_d(self.abw_g) / Decimal(self.doc)).quantize(Decimal('0.001')) if self.doc and self.abw_g else Decimal('0')

        stocking = Stocking.objects.filter(pond=self.pond, date__lte=self.date).order_by('-date').first()
        if stocking and not self.stocking_count:
            self.stocking_count = stocking.seed_count

        if not self.cumulative_feed_kg:
            feed_total = DailyPondRecord.objects.filter(pond=self.pond, date__lte=self.date).aggregate(s=models.Sum('daily_feed_kg'))['s'] or Decimal('0')
            self.cumulative_feed_kg = feed_total
        latest_feed = DailyPondRecord.objects.filter(pond=self.pond, date__lte=self.date).order_by('-date').first()
        if latest_feed and not self.daily_feed_kg:
            self.daily_feed_kg = latest_feed.daily_feed_kg or Decimal('0')

        fd = _d(self.daily_feed_kg)
        fr = _d(self.fr_percent)
        self.biomass_kg = (fd / fr * Decimal('100')).quantize(Decimal('0.01')) if fd and fr else Decimal('0')
        self.population = int((_d(self.biomass_kg) * _d(self.size)).quantize(Decimal('1'))) if self.biomass_kg and self.size else 0
        if self.stocking_count:
            self.estimated_sr = (_d(self.population) / Decimal(self.stocking_count) * Decimal('100')).quantize(Decimal('0.01'))
        else:
            self.estimated_sr = Decimal('0')

        if not self.population_index:
            self.population_index = self.population
        self.biomass_index_kg = (_d(self.population_index) / _d(self.size, '1')).quantize(Decimal('0.01')) if self.population_index and self.size else Decimal('0')
        if self.stocking_count:
            self.sr_index_percent = (_d(self.population_index) / Decimal(self.stocking_count) * Decimal('100')).quantize(Decimal('0.01'))
        else:
            self.sr_index_percent = Decimal('0')

        self.fcr = (_d(self.cumulative_feed_kg) / _d(self.biomass_kg, '1')).quantize(Decimal('0.001')) if self.biomass_kg and self.cumulative_feed_kg else Decimal('0')

        if not self.harvest_estimation:
            target_size = Decimal('50')
            current_size = _d(self.size)
            adg = _d(self.adg_weekly) or _d(self.adg_cumulative) or Decimal('0.15')
            if current_size and current_size > target_size and adg > 0:
                target_abw = Decimal('1000') / target_size
                days_needed = max(int((target_abw - _d(self.abw_g)) / adg), 0)
                est_date = self.date + timedelta(days=days_needed)
                self.harvest_estimation = f'Estimasi size 50 sekitar {est_date.strftime("%d/%m/%Y")}'
            else:
                self.harvest_estimation = 'Sudah mendekati target panen parsial.'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Sampling {self.pond} - DOC {self.doc}'


class SiphonRecord(models.Model):
    cycle = models.ForeignKey(CultivationCycle, on_delete=models.PROTECT, null=True, blank=True, related_name='%(class)s_records')
    pond = models.ForeignKey(Pond, on_delete=models.CASCADE, related_name='siphon_records')
    technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(default=timezone.localdate)
    doc = models.PositiveIntegerField(default=0)
    dead_count = models.PositiveIntegerField(default=0)
    live_count = models.PositiveIntegerField(default=0)
    daily_total = models.PositiveIntegerField(default=0)
    accumulated_total = models.PositiveIntegerField(default=0)
    health_indicator = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', 'pond__name']
        unique_together = [('pond', 'date')]

    def save(self, *args, **kwargs):
        self.daily_total = (self.dead_count or 0) + (self.live_count or 0)
        previous_total = SiphonRecord.objects.filter(pond=self.pond, date__lt=self.date).aggregate(s=models.Sum('daily_total'))['s'] or 0
        self.accumulated_total = previous_total + self.daily_total
        if self.dead_count >= 100:
            self.health_indicator = 'Risiko tinggi - mortalitas meningkat'
        elif self.dead_count >= 30:
            self.health_indicator = 'Waspada - pantau kualitas air dan anco'
        elif self.dead_count > 0:
            self.health_indicator = 'Normal terkendali'
        else:
            self.health_indicator = 'Aman'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Siphon {self.pond} - {self.date}'
