import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import pandas as pd

BIN = Path(__file__).resolve().parents[1] / 'bin'
sys.path.insert(0, str(BIN))
with patch.dict(sys.modules, {'duckdb': types.ModuleType('duckdb'),
                              'liftover': types.ModuleType('liftover')}):
    spec = importlib.util.spec_from_file_location('map_to_build_nf', BIN / 'map_to_build_nf.py')
    mapper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mapper)


class RsidAliasTest(unittest.TestCase):
    def test_alias_fills_missing_values_and_preserves_existing_ids(self):
        df = pd.DataFrame({'rs_id': ['rs33924890', 'rs5827412', 'rs3', 'rs4', 'NA'],
                           'rsid': [None, '#NA', 'rs3', 'rs9', None]})
        warning = io.StringIO()
        with contextlib.redirect_stderr(warning):
            mapper.add_fields_if_missing(df)
        self.assertEqual(df['rsid'].tolist()[:4], ['rs33924890', 'rs5827412', 'rs3', 'rs9'])
        self.assertTrue(pd.isna(df['rsid'][4]))
        self.assertIn('1 rows', warning.getvalue())
        self.assertEqual(df['rs_id'][0], 'rs33924890')

    def test_only_alias_and_neither_column(self):
        df = pd.DataFrame({'rs_id': ['rs5827412']})
        mapper.add_fields_if_missing(df)
        self.assertEqual(df['rsid'].tolist(), ['rs5827412'])
        df = pd.DataFrame({'chromosome': ['8']})
        mapper.add_fields_if_missing(df)
        self.assertEqual(df['rsid'].tolist(), ['NA'])

    def test_only_rsid(self):
        df = pd.DataFrame({'rsid': ['rs33924890']})
        mapper.add_fields_if_missing(df)
        self.assertEqual(df['rsid'].tolist(), ['rs33924890'])


if __name__ == '__main__':
    unittest.main()
