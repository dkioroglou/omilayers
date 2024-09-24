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
        self.engine = 'sqlite'

    def test_01_initialization(self):
        omi = Omilayers(self.db, engine=self.engine)
        # Database was created
        self.assertTrue(Path(self.db).exists())
        # Table "tables_info" has been created
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name='tables_info'"
        result = self._dbutils._sqlite_execute_fetch_query(query, fetchall=False)
        self.assertEqual("tables_info", result[0])

    def test_02_create_table_from_pandas(self):
        omi = Omilayers(self.db, engine=self.engine)
        df = pd.DataFrame({
            'col1': np.arange(1, 11),
            'col2': np.arange(11, 21),
            'col3': np.arange(21, 31)
            })
        omi.layers['first_layer'] = df
        # Table "first_layer" was created
        tables = self._dbutils._get_tables_names()
        self.assertIn("first_layer", tables)
        # Dataframe data were stored correctly.
        dfLoaded = omi.layers['first_layer'].to_df()
        self.assertTrue(np.array_equal(df.values, dfLoaded.values))

    def test_03_get_columns_of_stored_layer(self):
        omi = Omilayers(self.db, engine=self.engine)
        columns = omi.layers['first_layer'].columns
        self.assertTrue(np.array_equal(np.array(columns), np.array(['col1', 'col2', 'col3'])))

    def test_04_set_and_get_layer_info(self):
        omi = Omilayers(self.db, engine=self.engine)
        omi.layers['first_layer'].set_info("This is the first layer.")
        layerInfo = omi.layers['first_layer'].info
        self.assertTrue(layerInfo == "This is the first layer.")

    def test_05_set_and_get_layer_tag(self):
        omi = Omilayers(self.db, engine=self.engine)
        omi.layers['first_layer'].set_tag("data")
        layerTag = omi.layers['first_layer'].tag
        self.assertTrue(layerTag == "data")

    def test_06_replace_layer_data(self):
        omi = Omilayers(self.db, engine=self.engine)
        df = pd.DataFrame({
            'col1': np.arange(101, 111),
            'col2': np.arange(111, 121),
            'col3': np.arange(121, 131),
            'col4': np.arange(131, 141)
            })
        omi.layers['first_layer'].set_data(df)
        # Check layer data have been changed
        dfStored = omi.layers['first_layer'].to_df()
        self.assertTrue(np.array_equal(df.values, dfStored.values))
        # Check info and tag remained unchanged
        layerInfo = omi.layers['first_layer'].info
        self.assertTrue(layerInfo == "This is the first layer.")
        layerTag = omi.layers['first_layer'].tag
        self.assertTrue(layerTag == "data")

    def test_07_insert_new_unordered_data_to_layer(self):
        omi = Omilayers(self.db, engine=self.engine)
        data = pd.DataFrame({'col2':[400], 'col3':[300], 'col1':[1000], 'col4':[400]})
        omi.layers['first_layer'].insert(data, ordered=False)
        lastRow = omi.layers['first_layer'].to_df().iloc[-1,:].values
        self.assertTrue(np.array_equal(lastRow, np.array([1000, 400, 300, 400])))

    def test_08_insert_new_unordered_data_from_dict_to_layer(self):
        omi = Omilayers(self.db, engine=self.engine)
        data = {'col2':[4000], 'col3':[3000], 'col1':[10000], 'col4':[4000]}
        omi.layers['first_layer'].insert(data, ordered=False)
        lastRow = omi.layers['first_layer'].to_df().iloc[-1,:].values
        self.assertTrue(np.array_equal(lastRow, np.array([10000, 4000, 3000, 4000])))

    def test_09_select_columns_from_stored_layer_with_where_clause(self):
        omi = Omilayers(self.db, engine=self.engine)
        df = omi.layers['first_layer'].select(cols=['col1', 'col2'], where='col3', values=3000)
        self.assertTrue(np.array_equal(df.iloc[0,:].values, np.array([3000, 10000,  4000])))

    def test_10_select_columns_from_stored_layer_with_query(self):
        omi = Omilayers(self.db, engine=self.engine)
        df = omi.layers['first_layer'].query("col3 == 3000 or col3 == 300", cols=['col1'])
        self.assertTrue(np.array_equal(df['col1'].values, np.array([1000,  10000])))

    def test_11_rename_column_of_stored_layer(self):
        omi = Omilayers(self.db, engine=self.engine)
        omi.layers['first_layer'].rename(col='col4', new_name='col5')
        layerCols = omi.layers['first_layer'].columns
        self.assertNotIn('col4', layerCols)
        self.assertIn('col5', layerCols)

    def test_12_delete_column_from_stored_layer(self):
        omi = Omilayers(self.db, engine=self.engine)
        omi.layers['first_layer'].drop("col5")
        layerCols = omi.layers['first_layer'].columns
        self.assertNotIn('col5', layerCols)

    def test_13_delete_rows_from_stored_layer(self):
        omi = Omilayers(self.db, engine=self.engine)
        omi.layers['first_layer'].drop(col="col3", values=3000)
        colValues = omi.layers['first_layer']['col3']
        self.assertNotIn(3000, colValues)

    def test_14_create_json_with_two_columns_of_layer(self):
        omi = Omilayers(self.db, engine=self.engine)
        JSON = omi.layers['first_layer'].to_json(key_col='col1', value_col="col2")
        keysSum = 0
        for key in JSON:
            keysSum += key
        self.assertTrue(keysSum == 2055)
        valuesSum = 0
        for key in JSON:
            valuesSum += JSON[key]
        self.assertTrue(valuesSum == 1555)

    def test_15_replace_column_values_of_layer(self):
        omi = Omilayers(self.db, engine=self.engine)
        omi.layers['first_layer']['col1'] = pd.DataFrame({'col1':np.arange(1,12)})
        colValues = omi.layers['first_layer']['col1']
        self.assertTrue(np.array_equal(colValues, np.arange(1,12)))

if __name__ == '__main__':
    unittest.main()


