"""Regression test untuk pemetaan kolom template import sampling."""
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile

from django.test import TestCase
from openpyxl import Workbook

from ponds.models import Pond
from operations.excel_import import parse_sampling


class SamplingImportParserTest(TestCase):
    def setUp(self):
        self.pond = Pond.objects.create(code='K1', name='Kolam 1')

    def test_compact_template_columns_are_mapped_by_header(self):
        wb = Workbook()
        ws = wb.active
        ws.title = 'Data Sampling'
        ws.append([
            'Kolam', 'Tanggal', 'DOC', 'Berat SHRIMP (gr)',
            'Jumlah SHRIMP (ekor)', 'ADG Weekly Target',
            'Pakan Kumulatif (Kg)', 'Tebar', 'F/D Pakan Harian',
            'FR (%)', 'Populasi Index', 'Index', 'Catatan',
        ])
        ws.append(['K1', date(2026, 7, 12), 57, 981, 95, 0.25,
                   2077.5, 186386, 89, 4.49, 226000, 0.68, 'Normal'])
        with NamedTemporaryFile(suffix='.xlsx') as fh:
            wb.save(fh.name)
            rows = parse_sampling(fh.name)

        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]['valid'])
        data = rows[0]['data']
        self.assertEqual(data['cumulative_feed_kg'], '2077.5')
        self.assertEqual(data['stocking_count'], 186386)
        self.assertEqual(data['daily_feed_kg'], '89')
        self.assertEqual(data['fr_percent'], '4.49')
        self.assertEqual(data['population_index'], 226000)
        self.assertEqual(data['index_score'], '0.68')
