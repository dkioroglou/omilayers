import unittest
from pathlib import Path
import pandas as pd
import numpy as np
import os
from omilayers import Omilayers
from omilayers.engines.sqlite.dbclass import DButils

class TestSqlEngine(unittest.TestCase):

    def setUp(self):
        self.db = os.path.expanduser("~/Desktop/test.sqlite")
        self._dbutils = DButils(self.db, config={}, read_only=False)

    def test_initialization(self):
        omi = Omilayers(self.db, engine='sqlite')
        # Database was created
        self.assertTrue(Path(self.db).exists())
        # Table "tables_info" has been created
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name='tables_info'"
        result = self._dbutils._sqlite_execute_fetch_query(query, fetchall=False)
        self.assertEqual("tables_info", result[0])

    def test_create_table_from_pandas(self):
        omi = Omilayers(self.db, engine='sqlite')
        df = pd.DataFrame({
            'col1': np.arange(1, 11),
            'col2': np.arange(11, 21),
            'col3': np.arange(21, 31)
            })
        omi.layers['first_layer'] = 'df'
        tables = self._dbutils._get_tables_names()
        self.assertIn("first_layer", tables)

        dfLoaded = omi.layers['first_layer'].to_df()
        self.assertTrue(df.equals(dfLoaded))
        
if __name__ == '__main__':
    unittest.main()


