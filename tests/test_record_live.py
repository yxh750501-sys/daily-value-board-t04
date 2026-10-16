from datetime import datetime
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from record_live import upsert

RAW = {'timezone': 'Asia/Seoul', 'current': {'time': '2026-10-16T09:00', 'temperature_2m': 17.4},
       'current_units': {'temperature_2m': '°C'}}

class RecordLiveTests(unittest.TestCase):
    def test_same_day_upsert_and_next_day(self):
        first = upsert({}, RAW, '2026-10-16T00:00:00.000Z')
        self.assertEqual(first['readings'][0]['normalized_value'], 17.4)
        self.assertEqual(first['readings'][0]['source_time'], '2026-10-16T00:00:00.000Z')
        changed = {**RAW, 'current': {'time': '2026-10-16T10:00', 'temperature_2m': 18.1}}
        second = upsert(first, changed, '2026-10-16T01:00:00.000Z')
        self.assertEqual(len(second['readings']), 1)
        self.assertEqual(second['readings'][0]['normalized_value'], 18.1)
        tomorrow = {**RAW, 'current': {'time': '2026-10-17T09:00', 'temperature_2m': 19.2}}
        third = upsert(second, tomorrow, '2026-10-17T00:00:00.000Z')
        self.assertEqual([row['record_date'] for row in third['readings']], ['2026-10-16', '2026-10-17'])
        self.assertEqual(third['raw_by_date']['2026-10-16']['current']['temperature_2m'], 18.1)

    def test_invalid_value_preserves_input(self):
        first = upsert({}, RAW, '2026-10-16T00:00:00.000Z')
        invalid = {**RAW, 'current': {'time': '2026-10-16T09:00', 'temperature_2m': '17.4'}}
        with self.assertRaises(ValueError):
            upsert(first, invalid, '2026-10-16T01:00:00.000Z')
        self.assertEqual(first['readings'][0]['normalized_value'], 17.4)

if __name__ == '__main__':
    unittest.main()
