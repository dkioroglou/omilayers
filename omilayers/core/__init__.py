import duckdb
from pathlib import Path
from typing import List, Dict, Union
from omilayers import utils
import pandas as pd
import numpy as np
import inspect

class Stack:

    def __init__(self, db:str, config:str, read_only:bool, dbutilsClass):
        self.db = db
        self.config = config
        self.read_only = read_only
        # self._dbutils = DButils(db, config, read_only=read_only)
        self._dbutils = dbutilsClass
        self._layers = dict()
        if Path(self.db).exists():
            layerNames = self._dbutils._get_tables_names()
            for name in layerNames:
                self._layers[name] = Layer(name, data=None, dbutilsClass=self._dbutils)

    def drop(self, layer:str) -> None:
        """
        Delete layer.

        Parameters
        ----------
        layer: str
            The name of the layer to delete.
        """
        self._layers.pop(layer, None)
        if self._dbutils._table_exists(layer):  
            self._dbutils._drop_table(layer)

    def rename(self, layer:str, new_name:str) -> None:
        """
        Rename layer.

        Parameters
        ----------
        layer: str
            Current name of layer.
        new_name: str
            The new name of the layer.
        """
        self._layers.pop(layer, None)
        self._layers[new_name] = Layer(new_name, data=None, dbutilsClass=self._dbutils)
        self._dbutils._rename_table(layer, new_name)
        self._dbutils._update_tables_info(layer, "name", new_name)

    def search(self, term:str) -> None:
        """
        Search for layers based on a given term. Useful in situations where there are many layers and there is doubt which table holds a given information or data. The term is searched across layer names, layer columns and layer descriptions. 

        Parameters
        ----------
        term: str
            Term to be search across layer names, layer columns and layer descriptions.

        Returns
        -------
        Prints the names of the layers that matched the searched term.
        """
        JSON = {}
        for layer in self._layers.keys():
            if term.lower() in layer.lower():
                if not JSON.get(layer, False):
                    JSON[layer] = "found"
            if term.lower() in self._layers[layer].info.lower():
                if not JSON.get(layer, False):
                    JSON[layer] = "found"

            layerCols = self._layers[layer].columns
            for col in layerCols:
                if term.lower() in col.lower():
                    if not JSON.get(layer, False):
                        JSON[layer] = "found"

        if len(JSON.keys()) > 0:
            layers = list(JSON.keys())
            tableCols = self._dbutils._get_table_column_names("tables_info")
            df = self._dbutils._select_rows(table="tables_info", cols=tableCols, where="name", values=layers)
            df = df.iloc[:, 1:] # Query introduces the "where" column in the dataframe and it repeats.
            df = df[tableCols] # order column names
            print(df.to_string(index=False))
        else:
            print("Term was not found in any layer.")

    def from_csv(self, layer:str, filename:str, chunksize:Union[int,None]=None, *args, **kwargs) -> None:
        """
        Create layer from a csv file. For large csv files, set chunksize to the number of rows that will be read each time from the file.

        Parameters
        ----------
        layer: str
            The name of the layer to be created.
        filename: str
            The input csv file.
        chunksize: int, None
            The number of rows that will be read each time from the file. If None, the whole csv file will be read.
        *args, **kwargs: arguments and keywords as defined by pandas.read_csv
        """
        if chunksize is not None:
            layerExists = self._dbutils._table_exists(layer)
            with pd.read_csv(filename, chunksize=chunksize, *args, **kwargs) as infile:
                for dftmp in infile:
                    if not layerExists:
                        self._layers[layer] = Layer(layer, data=dftmp, dbutilsClass=self._dbutils)
                        layerExists = True
                    else:
                        self._dbutils._insert_rows(table=layer, data=dftmp, ordered=True)
        else:
            data = pd.read_csv(filename, *arg, **kwargs)
            self._layers[layer] = Layer(layer, data, self._dbutils)

    def __getitem__(self, layer:str) -> pd.DataFrame:
        if not self._layers.get(layer, False):
            raise ValueError(f"Layer '{layer}' does not exist.")
        return self._layers[layer]

    def __setitem__(self, layer:str, data:Union[pd.DataFrame,None]):
        self._layers[layer] = Layer(layer, data, self._dbutils)

    def __call__(self, tag:Union[None,str]=None) -> pd.DataFrame:
        df = self._dbutils._select_cols(table="tables_info", cols="*")
        if tag is None:
            return df
        return df.query(f"tag == '{tag}'")

    def __repr__(self):
        df = self._dbutils._get_tables_info()
        return df.to_string(index=False)


class Selector:

    def __init__(self, layer, dbutilsClass) -> None:
        self._dbutils = dbutilsClass
        self.layer = layer

    def __getitem__(self, indices) -> pd.DataFrame:
        if len(indices) < 2:
            raise ValueError("Rows and Columns should be specified.")
        if len(indices) == 2:
            whereCol = "rowid"
            rowValues, columns = indices
        else:
            rowValues, columns, whereCol = indices = indices
        return self._dbutils._select_rows(table=self.layer, cols=columns, where=whereCol, values=rowValues)


class Layer:

    def __init__(self, name:str, data:Union[pd.DataFrame,None], dbutilsClass) -> None:
        self._dbutils = dbutilsClass
        self.name = name
        self.loc = Selector(name, self._dbutils)
        if data is not None:
            try:
                self._dbutils._create_table_from_pandas(table=name, data=data)
            except Exception as error:
                print(error)

    @property
    def exists(self) -> bool:
        """Check layer exists."""
        if self._dbutils._table_exists(self.name):
            return True
        return False

    @property
    def columns(self) -> List:
        """Get the columns of the layer."""
        return self._dbutils._get_table_column_names(self.name)

    @property
    def info(self) -> Union[str,List]:
        """Get the description of the layer."""
        return self._dbutils._get_from_tables_info(table=self.name, col="info")

    @property
    def tag(self) -> Union[str,List]:
        """Get the assigned tag of the layer."""
        return self._dbutils._get_from_tables_info(table=self.name, col="tag")

    def set_info(self, value:str) -> None:
        """Change the description of the layer."""
        self._dbutils._update_tables_info(table=self.name, col="info", value=value)

    def set_tag(self, value:str) -> None:
        """Change the assigned tag of the layer."""
        self._dbutils._update_tables_info(table=self.name, col="tag", value=value)

    def set_data(self, data:pd.DataFrame) -> None:
        """
        Change the data the layer currently holds.

        Parameters
        ----------
        data: pandas.DataFrame 
            A pandas.DataFrame object.
        """
        try:
            layerCurrentInfo = self.info
            layerCurrentTag = self.tag
            self._dbutils._create_table_from_pandas(table=self.name, data=data)
            self.set_info(layerCurrentInfo)
            self.set_tag(layerCurrentTag)
        except Exception as error:
            print(error)

    def insert(self, data:Union[Dict,pd.DataFrame], ordered:bool=False) -> None:
        """
        Insert new rows of data to an existing layer.

        Parameters
        ----------
        data: pandas.DataFrame, dict
            Pass a pandas.DataFrame object. The rows of the pandas.DataFrame will be inserted as new layer rows. Alternatively, pass a dictionary with keys the names of the columns of the layer and values the data to be inserted as rows.
        ordered: bool
            Pass True only in case data is string, and the order of the columns in the referred pandas.DataFrame matches the order of the layer's columns.
        """
        if isinstance(data, dict):
            firstKey = list(data.keys())[0]
            if isinstance(data[firstKey], str) or isinstance(data[firstKey], int) or isinstance(data[firstKey], float):
                Nrows = 1
            else:
                Nrows = len(data[firstKey])
            dfData = pd.DataFrame(data, index=list(range(Nrows)))
            self._dbutils._insert_rows(table=self.name, data=dfData)
        else:
            self._dbutils._insert_rows(table=self.name, data=data, ordered=ordered)

    def select(self, cols:Union[str,List], where:str, values:Union[str,int,float,slice,np.ndarray,List], exclude:Union[str,List,None]=None) -> pd.DataFrame:
        """
        Select columns from layer where a reference column has rows with certain values.

        Parameters
        ----------
        cols: str, list
            The columns to select from layer. If cols='*' all columns are selected.
        where: str
            The name of the reference column in the layer.
        values: str, int, float, np.ndarray, list
            The values the reference column to be used during row selection. 
        exclude: str, list
            Useful in cases where large number of columns need to selected except few ones.

        Returns
        -------
        A pandas.DataFrame with the selected columns and the filtered rows.
        """
        df = self._dbutils._select_rows(table=self.name, cols=cols, where=where, values=values)
        if df.shape[1] == 1:
            return df.iloc[:, 0].values
        return df

    def query(self, condition:str, cols:Union[str,List]='*') -> pd.DataFrame:
        """
        Select one or more columns from layer given condition.

        Parameters
        ----------
        cols: str, list
            One or more columns to be selected from layer. If col='*' all columns will be selected.
        condition: str
            The condition to be matched during selection. For instance, when a given column has a given value.

        Returns
        -------
        A pandas.DataFrame with the selected columns and the filtered rows.
        """
        if isinstance(cols, list):
            cols = ",".join(utils._sanitize_column_names(cols))
        elif isinstance(cols, str) and cols != "*":
            cols = f'"{cols}"'
        condition = condition.replace('`', '"')
        queryText = f'SELECT rowid,{cols} FROM {self.name} WHERE {condition}'
        df = self._dbutils._execute_select_query(queryText)
        if df.shape[1] == 1:
            return df.iloc[:, 0].values
        df = df.set_index("rowid")
        return df

    def rename(self, col:str, new_name:str) -> None:
        """
        Rename a column in layer.

        Parameters
        ----------
        col: str
            Current name of column in layer.
        new_name: str
            New name of column.
        """
        self._dbutils._rename_column(table=self.name, col=col, new_name=new_name)

    def drop(self, col:Union[str,None]=None, values:Union[None,str,int,float,List]=None) -> None:
        """
        Delete column or rows from layer.

        Parameters
        ----------
        col: str, None
            Name of column in layer.
        values: str, int, float, list, None
            if None, whole column will be deleted. Otherwise, rows that match values in column will be deleted. If column is None, values correspond to rowids.
        """

        if col is None:
            if not isinstance(values, int) or not isinstance(values, list):
                raise ValueError("Pass integer or list of integers when not specifying column.")
            self._dbutils._delete_rows(table=self.name, where_col="rowid", where_values=values)
        else:
            if values is None:
                self._dbutils._drop_column(table=self.name, col=col)
            else:
                self._dbutils._delete_rows(table=self.name, where_col=col, where_values=values)

    def to_df(self, index:Union[str,None]=None) -> pd.DataFrame:
        """
        Load layer as pandas.DataFrame.

        Parameters
        ----------
        index: str, None
            The column to be used as pandas.DataFrame index.
        """
        if index:
            return self._dbutils._select_cols(table=self.name, cols="*").set_index(index)
        return self._dbutils._select_cols(table=self.name, cols="*")

    def to_json(self, key_col:str, value_col:str) -> dict:
        """
        Create dictionary using two columns of layer

        Parameters
        -----------
        key_col: str
            Layer's column whose values are going to be used as dictionary keys.
        value_col: str
            Layer's column whose values are going to be used as dictionary values.

        Returns
        -------
        Python dictionary.
        """
        df = self._dbutils._select_cols(table=self.name, cols=[key_col, value_col])
        return {x:y for x,y in zip(df[key_col], df[value_col])}

    def __getitem__(self, features:Union[str,int,List,slice]) -> pd.DataFrame:
        if isinstance(features, slice) or isinstance(features, int):
            columns = self._dbutils._get_table_column_names(self.name)
            df = self._dbutils._select_cols(table=self.name, cols=columns[features])
        elif isinstance(features, str):
            df = self._dbutils._select_cols(table=self.name, cols=[features])
        elif isinstance(features, list):
            df = self._dbutils._select_cols(table=self.name, cols=features)
        if df.shape[1] == 1:
            df = df.iloc[:,0].values
        return df

    def __setitem__(self, feature:str, data:Union[pd.Series,np.ndarray,List]):
        existing_features = self._dbutils._get_table_column_names(self.name)
        if feature in existing_features:
            self._dbutils._update_column(table=self.name, col=feature, data=data)
        else:
            self._dbutils._add_column(table=self.name, col=feature, data=data)

    def __repr__(self):
        df = self._dbutils._select_cols(table=self.name, cols="*", limit=1)
        df1 = pd.DataFrame(df.dtypes).reset_index()
        df1 = df1.rename(columns={"index":"column", 0:"dtype"})
        df2 = pd.DataFrame(df.iloc[0, :].values, columns=['values'])
        return repr(pd.concat([df1, df2], axis='columns'))
