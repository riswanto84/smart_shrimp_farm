from datetime import date
from decimal import Decimal

from django.test import TestCase

from cultivation.models import CultivationCycle
from ponds.models import Pond
from operations.models import SamplingRecord


class SamplingExcelFormulaTests(TestCase):
    def setUp(self):
        self.pond = Pond.objects.create(code='K1', name='Kolam 1')
        self.cycle = CultivationCycle.objects.create(
            name='Siklus Uji', start_date=date(2026, 7, 1), status='active'
        )

    def test_excel_formula_mapping_and_previous_sample(self):
        SamplingRecord.objects.create(
            cycle=self.cycle,
            pond=self.pond,
            date=date(2026, 7, 1),
            doc=29,
            sample_weight_g=Decimal('245'),
            sample_count=88,
            daily_feed_kg=Decimal('33'),
            fr_percent=Decimal('6.51'),
            stocking_count=186386,
            cumulative_feed_kg=Decimal('449.8'),
            population_index=225000,
            index_score=Decimal('0.5'),
        )
        second = SamplingRecord.objects.create(
            cycle=self.cycle,
            pond=self.pond,
            date=date(2026, 7, 8),
            doc=36,
            sample_weight_g=Decimal('288'),
            sample_count=68,
            adg_weekly_target=Decimal('0.25'),
            daily_feed_kg=Decimal('45'),
            fr_percent=Decimal('6.11'),
            stocking_count=186386,
            cumulative_feed_kg=Decimal('722.53'),
            population_index=226000,
            index_score=Decimal('0.52'),
        )

        self.assertEqual(second.abw_g, Decimal('4.24'))
        self.assertEqual(second.abw_last_g, Decimal('2.78'))
        self.assertEqual(second.sampling_interval_days, 7)
        self.assertEqual(second.abw_target_g, Decimal('4.53'))
        self.assertEqual(second.target_size, Decimal('220.75'))
        self.assertEqual(second.adg_weekly, Decimal('0.209'))
        self.assertEqual(second.adg_cumulative, Decimal('0.118'))
        self.assertEqual(second.biomass_kg, Decimal('736.50'))
        self.assertEqual(second.population_index, 226000)

    def test_population_index_is_not_replaced_by_fr_population(self):
        sample = SamplingRecord.objects.create(
            cycle=self.cycle,
            pond=self.pond,
            date=date(2026, 7, 1),
            doc=29,
            sample_weight_g=Decimal('245'),
            sample_count=88,
            daily_feed_kg=Decimal('33'),
            fr_percent=Decimal('6.51'),
            stocking_count=186386,
            population_index=0,
        )
        self.assertEqual(sample.population_index, 0)
        self.assertEqual(sample.biomass_index_kg, Decimal('0'))
        self.assertEqual(sample.sr_index_percent, Decimal('0'))
