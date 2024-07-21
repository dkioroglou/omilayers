import duckdb
import numpy as np
import pandas as pd
from typing import List, Union
import warnings

def convert_to_duckdb_dtypes(data:Union[pd.DataFrame, pd.Series, np.array, List]) -> List:
    """Convert data types of input data to duckdb data types."""
    duckdbDtypes = []
    data = pd.DataFrame(data)
    for col in data.columns:
        if data[col].dtype == "int":
            duckdbDtypes.append("INTEGER")
        elif data[col].dtype == "float":
            duckdbDtypes.append("DOUBLE")
        else:
            duckdbDtypes.append("VARCHAR")
    return duckdbDtypes

def create_query_placeholders(data:Union[List, np.ndarray, pd.DataFrame, pd.Series]):
    if isinstance(data, pd.DataFrame):
        Ncols = data.shape[1]
    elif isinstance(data, pd.Series):
        Ncols = 1
    elif isinstance(data, list):
        if len(np.array(list).shape) == 1:
            Ncols = 1
        else:
            Ncols = np.array(data).shape[1]
    elif isinstance(data, np.ndarray):
        if len(data.shape) == 1:
            Ncols = 1
        else:
            Ncols = data.shape[1]
    return str(tuple(list('?')*Ncols)).replace("'", "")

def create_data_array_for_query(data:Union[List, np.ndarray, pd.Series, pd.DataFrame], rowids:Union[List,np.ndarray,None]=None) -> List:
    """Convert data to duckdb digestible data format. If rowid is True, a rowid will be added to the data."""
    if rowids is None:
        if isinstance(data, pd.DataFrame):
            return data.values.tolist()
        elif isinstance(data, np.ndarray):
            if len(data.shape) == 1:
                return [[value] for value in data]
            else:
                return data.tolist()
        elif isinstance(data, list):
            if len(np.array(data).shape) == 1:
                return [[value] for value in data]
        return data
    else:
        if isinstance(rowids, np.ndarray):
            rowids = rowids.tolist()
        if isinstance(data, pd.DataFrame):
            data['rowid'] = rowids
            return data.values.tolist()
        else:
            df = pd.DataFrame(data)
            df['rowid'] = rowids
            return df.values.tolist()


