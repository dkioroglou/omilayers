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

def convert_to_sqlite_dtypes(data:Union[pd.DataFrame, pd.Series, np.array, List]) -> List:
    """Convert data types of input data to sqlite data types."""
    sqliteDtypes = []
    data = pd.DataFrame(data)
    for col in data.columns:
        if data[col].dtype == "int":
            sqliteDtypes.append("INTEGER")
        elif data[col].dtype == "float":
            sqliteDtypes.append("REAL")
        else:
            sqliteDtypes.append("TEXT")
    return sqliteDtypes

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
    if Ncols == 1:
        return "(?)"
    return str(tuple(list('?')*Ncols)).replace("'", "")

def create_data_array_for_duckdb_query(data:Union[List, np.ndarray, pd.Series, pd.DataFrame], rowids:Union[List,np.ndarray,None]=None) -> List:
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

def create_data_array_for_sqlite_query(data:Union[List, np.ndarray, pd.Series, pd.DataFrame], rowids:Union[List,np.ndarray,None]=None) -> List:
    """Convert data to sqlite digestible data format. If rowid is True, a rowid will be added to the data."""
    if rowids is None:
        if isinstance(data, pd.DataFrame):
            return [x.tolist() for x in data.to_records(index=False)]
        elif isinstance(data, np.ndarray):
            if len(data.shape) == 1:
                return [(value,) for value in data]
            else:
                return [tuple(x) for x in data.tolist()]
        elif isinstance(data, list):
            if len(np.array(data).shape) == 1:
                return [(value,) for value in data]
        return data
    else:
        if isinstance(rowids, np.ndarray):
            rowids = rowids.tolist()
        if isinstance(data, pd.DataFrame):
            data['rowid'] = rowids
            return [x.tolist() for x in data.to_records(index=False)]
        else:
            df = pd.DataFrame(data)
            df['rowid'] = rowids
            return [x.tolist() for x in df.to_records(index=False)]


def _dataframe_dtypes_to_sql_datatypes(df:pd.DataFrame) -> List:
    sqlDataTypes = []
    for item in df.dtypes.items():
        colName, colType = item
        if str(colType).startswith("int"):
            sqlDataTypes.append(f'"{colName}" INTEGER')
        elif str(colType).startswith("float"):
            sqlDataTypes.append(f'"{colName}" REAL')
        elif str(colType).startswith("object"):
            sqlDataTypes.append(f'"{colName}" TEXT')
        else:
            sqlDataTypes.append(f'"{colName}" TEXT')
    return sqlDataTypes

def _sanitize_column_names(cols:Union[np.ndarray, List]) -> List:
    sanitizedCols = []
    for col in cols:
        sanitizedCols.append(f'"{col}"')
    return sanitizedCols
