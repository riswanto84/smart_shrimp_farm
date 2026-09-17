from datetime import date, datetime, timedelta
from django.db import models
from django.utils import timezone


class CultivationCycle(models.Model):
    STATUS_PREPARATION = 'preparation'
    STATUS_ACTIVE = 'active'
    STATUS_HARVEST = 'harvest'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_PREPARATION, 'Persiapan'),
        (STATUS_ACTIVE, 'Aktif'),
        (STATUS_HARVEST, 'Panen'),
        (STATUS_COMPLETED, 'Selesai'),
    ]

    name = models.CharField(max_length=120, unique=True)
    start_date = models.DateField(default=timezone.localdate)
    target_duration_days = models.PositiveIntegerField(default=135)
    target_doc = models.PositiveIntegerField(default=120, help_text='Target DOC panen.')
    target_size = models.DecimalField(max_digits=6, decimal_places=2, default=30, help_text='Target size panen (ekor/kg).')
    target_biomass_ton = models.DecimalField(max_digits=10, decimal_places=2, default=25, help_text='Target biomassa/produksi dalam ton.')
    target_sr_percent = models.DecimalField(max_digits=6, decimal_places=2, default=85, help_text='Target survival rate dalam persen.')
    target_fcr = models.DecimalField(max_digits=6, decimal_places=2, default=1.20, help_text='Target feed conversion ratio.')
    target_adg = models.DecimalField(max_digits=7, decimal_places=3, default=0.25, help_text='Target ADG gram per hari.')
    target_population = models.PositiveBigIntegerField(default=0, blank=True, help_text='Field lama untuk kompatibilitas. Target populasi kini dihitung dari jumlah tebar × target SR.')
    estimated_price_per_kg = models.DecimalField(max_digits=14, decimal_places=2, default=0, blank=True, help_text='Harga jual estimasi per kilogram.')
    target_cost = models.DecimalField(max_digits=18, decimal_places=2, default=0, blank=True, help_text='Target biaya produksi satu siklus.')
    target_end_date = models.DateField(blank=True, null=True)
    actual_end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PREPARATION)
    notes = models.TextField(blank=True)
    final_snapshot = models.JSONField(default=dict, blank=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', '-id']

    @staticmethod
    def _coerce_date(value):
        """Konversi nilai tanggal dari form/manual assignment menjadi datetime.date."""
        if value in (None, ''):
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            value = value.strip()
            for date_format in ('%Y-%m-%d', '%d/%m/%Y'):
                try:
                    return datetime.strptime(value, date_format).date()
                except ValueError:
                    continue
            raise ValueError('Format tanggal tidak valid. Gunakan YYYY-MM-DD atau DD/MM/YYYY.')
        raise TypeError('Nilai tanggal harus berupa date, datetime, atau string tanggal.')

    def save(self, *args, **kwargs):
        if not self.target_duration_days:
            self.target_duration_days = 135

        # Perlindungan tambahan jika objek disimpan tanpa ModelForm.
        self.start_date = self._coerce_date(self.start_date)
        self.actual_end_date = self._coerce_date(self.actual_end_date)

        if self.start_date:
            # Hari pertama dihitung sebagai hari ke-1, sehingga target 135 hari berakhir +134 hari.
            self.target_end_date = self.start_date + timedelta(
                days=int(self.target_duration_days) - 1
            )
        else:
            self.target_end_date = None

        was_completed = False
        if self.pk:
            was_completed = type(self).objects.filter(pk=self.pk, status=self.STATUS_COMPLETED).exists()

        if self.status == self.STATUS_COMPLETED and not self.actual_end_date:
            self.actual_end_date = timezone.localdate()
        if self.status == self.STATUS_COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != self.STATUS_COMPLETED:
            self.completed_at = None

        super().save(*args, **kwargs)

        # Snapshot hanya dibuat saat transisi pertama menjadi selesai.
        if self.status == self.STATUS_COMPLETED and not was_completed and not self.final_snapshot:
            from .services import build_cycle_final_snapshot
            snapshot = build_cycle_final_snapshot(self)
            type(self).objects.filter(pk=self.pk).update(final_snapshot=snapshot)
            self.final_snapshot = snapshot

    @property
    def is_open(self):
        return self.status != self.STATUS_COMPLETED

    @property
    def progress_percent(self):
        if not self.start_date or not self.target_end_date:
            return 0
        today = self.actual_end_date or timezone.localdate()
        elapsed = (today - self.start_date).days + 1
        return max(0, min(100, round(elapsed / max(self.target_duration_days, 1) * 100)))


    def calculate_target_population(self, total_stocking):
        """Hitung target populasi hidup dari total tebar dan target SR."""
        if not total_stocking:
            return 0
        return round(int(total_stocking) * float(self.target_sr_percent or 0) / 100.0)

    @property
    def target_revenue(self):
        return self.target_biomass_ton * 1000 * self.estimated_price_per_kg

    @property
    def target_profit(self):
        return self.target_revenue - self.target_cost

    def __str__(self):
        return self.name
