from typing import List, Union
from pathlib import Path
from duckdb import fetchall
import numpy as np
import pandas as pd
from omilayers import utils
import contextlib
import sqlite3
import re


class DButils:

    def __init__(self, db, config, read_only):
        self.db = db
        self.config = config
        self.read_only = read_only
        if not Path(db).exists():
            self._create_table_for_tables_metadata()

    def _sqlite_execute_commit_query(self, query, values=None, get_changes=False) -> Union[str,None]:
        with contextlib.closing(sqlite3.connect(self.db)) as conn:
            with contextlib.closing(conn.cursor()) as c:
                if values is None:
                    c.execute(query)
                else:
                    c.execute(query, values)
                conn.commit()
                if get_changes:
                    query = "SELECT changes()"
                    c.execute(query)
                    result = c.fetchone()
                    return result[0]
        return None

    def _sqlite_executemany_commit_query(self, query, values:List) -> None:
        with contextlib.closing(sqlite3.connect(self.db)) as conn:
            with contextlib.closing(conn.cursor()) as c:
                c.executemany(query, values)
                conn.commit()

    def _sqlite_execute_fetch_query(self, query, fetchall:bool) -> List:
        with contextlib.closing(sqlite3.connect(self.db)) as conn:
            with contextlib.closing(conn.cursor()) as c:
                c.execute(query)
                if fetchall:
                    results = c.fetchall()
                else:
                    results = c.fetchone()
        return results

    def _create_table_for_tables_metadata(self) -> None:
        """Creates table with name 'tables_info' where layers info will be stored"""
        query = "CREATE TABLE IF NOT EXISTS tables_info (name TEXT PRIMARY KEY, tag TEXT, shape TEXT, info TEXT)"
        self._sqlite_execute_commit_query(query)

    def _get_tables_names(self, tag:str=None) -> List:
        """
        Get table names with or without a given tag.

        Parameters
        ----------
        tag: str, None
            If passed, tables names with specific tag will be fetched.

        Returns
        -------
        List of fetched tables.
        """
        if tag is None:
            query = f"SELECT name FROM tables_info"
        else:
            query = f"SELECT name FROM tables_info WHERE tag='{tag}'"
        results = self._sqlite_execute_fetch_query(query, fetchall=True)
        if results:
            tables = [res[0] for res in results]
        else:
            tables = []
        return tables

    def _update_table_shape(self, table:str, nrows:int=0, ncols:int=0) -> None:
        """
        Update table's shape.

        Parameters
        ----------
        table: str
            Name of table to update shape.
        nrows: int
            Number of new rows added.
        ncols: int
            Number of new columns added.
        """
        # Update table's shape
        tableRows, tableCols = self._get_table_shape(table)
        tableRows += nrows
        tableCols += ncols
        tableShape = f"{tableRows}x{tableCols}"
        query = f"UPDATE tables_info SET shape='{tableShape}' WHERE name='{table}'"
        self._sqlite_execute_commit_query(query)

    def _table_exists(self, table:str) -> bool:
        tables = self._get_tables_names() 
        if table in tables:
            return True
        return False

    def _get_table_rowids(self, table:str, limit:Union[int,None]=None) -> np.ndarray:
        if limit is None:
            query = f"SELECT rowid FROM {table}"
        else:
            query = f"SELECT rowid FROM {table} LIMIT {limit}"
        results = self._sqlite_execute_fetch_query(query, fetchall=True)
        if results:
            rowids = [res[0] for res in results]
        else:
            rowids = []
        return np.array(rowids)

    def _get_table_shape(self, table:str) -> tuple:
        query = f"SELECT shape from tables_info WHERE name='{table}'"
        result = self._sqlite_execute_fetch_query(query, fetchall=False) 
        if result:
            Nrows, Ncols = result[0].split("x")
            Nrows = int(Nrows)
            Ncols = int(Ncols)
        else:
            Nrows, Ncols = 0, 0
        return (Nrows, Ncols)

    def _delete_rows(self, table:str, where_col:str, where_values:Union[str,int,float,List]) -> None:
        """
        Delete one or more rows from table based on column values. 

        Parameters
        ----------
        table: str
            Name of existing table.
        where_col: str
            Name of column that will be used as reference to delete table rows.
        where_values: str, int, float, list
            The values of the reference column that are in the rows to be deleted. 
        """
        if isinstance(where_values, str):
            query = f"DELETE FROM {table} WHERE {where_col} = '{where_values}'"
        elif isinstance(where_values, int) or isinstance(where_values, float):
            query = f"DELETE FROM {table} WHERE {where_col} = {where_values}"
        else:
            values = ",".join(f"'{x}'" for x in where_values)
            query = f"DELETE FROM {table} WHERE {where_col} IN ({values})"
        deletedRows = self._sqlite_execute_commit_query(query, get_changes=True)
        self._update_table_shape(table, nrows=(deletedRows * -1))

    def _drop_table(self, table:str) -> None: 
        """
        Delete table if it exists.

        Parameters
        ----------
        table: str
            Name of table to delete.
        """
        query = f"DROP TABLE IF EXISTS {table}"
        self._sqlite_execute_commit_query(query)
        self._delete_rows(table="tables_info", where_col="name", where_values=table)

    def _create_table_from_pandas(self, table:str, data:pd.DataFrame) -> None:
        """
        Deletes previous created table if exists, creates then new table and inserts new values.

        Parameters
        ----------
        table: str
            The name of the table.
        data: pandas.DataFrame
            A pandas.DataFrame object.
        """

        if self._table_exists(table):
            self._drop_table(table)

        try:
            Nrows, Ncols = data.shape
            query = "INSERT INTO tables_info (name,shape) VALUES (?,?)"
            self._sqlite_execute_commit_query(query, values=(table,f"{Nrows}x{Ncols}"))
        except Exception as error:
            print(error)
            if table in self._select_cols(table='tables_info', cols='name')['name'].values.tolist():
                self._delete_rows(table='tables_info', where_col="name", where_values=table)

        try:
            query = 'CREATE TABLE "{}" ({})'.format(table, ", ".join(utils._dataframe_dtypes_to_sql_datatypes(data)))
            self._sqlite_execute_commit_query(query)

            queryPlaceHolders = utils.create_query_placeholders(data)
            sanitizedColumns = utils._sanitize_column_names(data.columns)
            query = f'INSERT INTO "{table}" ({",".join(sanitizedColumns)}) VALUES {queryPlaceHolders}'
            self._sqlite_executemany_commit_query(query, [x.tolist() for x in data.to_records(index=False)])
        except Exception as error:
            print(error)
            if self._table_exists(table):
                self._drop_table(table)

    def _select_cols(self, table:str, cols:Union[str,List], limit:Union[int,None]=None) -> pd.DataFrame:
        """
        Select columns from specified table.

        Parameters
        ----------
        table: str
            The name of the table to select columns from.
        cols: str, list
            The name of one or more columns to select. If string is "*" then all columns will be selected.
        limit: int, None
            Number of rows to fetch. If None, all rows will be fetched.

        Returns
        -------
        The selected columns from the specified table as pandas.DataFrame.
        """
        if isinstance(cols, str):
            if cols == "*":
                cols = self._get_table_column_names(table)
            else:
                cols = [cols]

        colsString = ','.join(utils._sanitize_column_names(cols))
        if limit is None:
            query = f"SELECT {colsString} FROM {table}"
        else:
            query = f"SELECT {colsString} FROM {table} LIMIT {limit}"
        data = self._sqlite_execute_fetch_query(query, fetchall=True)
        df = pd.DataFrame(data, columns=cols)
        return df.set_index(self._get_table_rowids(table, limit=limit))


    def _get_table_column_names(self, table:str, sanitized:bool=False) -> List:
        """
        Get the column names from a table.

        Parameters
        ----------
        table: str
            Name of table to fetch column names from.

        Returns
        -------
        List with column names from given table.
        """
        query = f"SELECT name FROM PRAGMA_TABLE_INFO('{table}');"
        results = self._sqlite_execute_fetch_query(query, fetchall=True)
        cols = [res[0] for res in results]
        if sanitized:
            cols = [f'"{res[0]}"' for res in results]
        else:
            cols = [res[0] for res in results]
        return cols

    def _insert_rows(self, table:str, data:pd.DataFrame, ordered:bool=False) -> None:
        """
        Insert one or more rows to table using pandas.DataFrame object.

        Parameters
        ----------
        table: str
            Name of the table to insert rows.
        data: pandas.DataFrame
            A pandas.DataFrame object.
        ordered: boolean
            True if the order of the columns in the pandas.DataFrame object matches the order of the column in table. False otherwise.
        """
        if not ordered:
            colsOrder = self._get_table_column_names(table)
            data = data[colsOrder]

        queryPlaceHolders = utils.create_query_placeholders(data)
        sanitizedCols = utils._sanitize_column_names(data.columns)
        query = f"INSERT INTO {table} ({','.join(sanitizedCols)}) VALUES {queryPlaceHolders}"
        self._sqlite_executemany_commit_query(query, [x.tolist() for x in data.to_records(index=False)])
        self._update_table_shape(table, nrows=data.shape[0])

    def _get_tables_info(self, tag:Union[None,str]=None) -> pd.DataFrame:
        """
        Get info for all tables, or for those in a given group tag.

        Parameters
        ----------
        tag: None, str
            If None, info from all tables will be returned. If str, info from tables that belogn to group tag will be returned.
        """
        cols = ['name', 'tag', 'shape', 'info']
        if tag is None: 
            query = f"SELECT {','.join(cols)} from tables_info"
        else:
            query = f"SELECT {','.join(cols)} from tables_info WHERE tag='{tag}'"
        results = self._sqlite_execute_fetch_query(query, fetchall=True)
        df = pd.DataFrame(results, columns=cols)
        return df

    def _rename_table(self, table:str, new_name:str) -> None:
        """
        Changes the name of an existing table.

        Parameters
        ----------
        table: str
            Name of existing table.
        new_name: str
            The new name of the table.
        """
        query = f"ALTER TABLE {table} RENAME TO {new_name}"
        self._sqlite_execute_commit_query(query)

    def _rename_column(self, table:str, col:str, new_name:str) -> None:
        """
        Changes the column name of an existing table.

        Parameters
        ----------
        table: str
            Name of existing table.
        col: str
            Existing name of column to be renamed.
        new_name: str
            New name of column.
        """
        query = f'ALTER TABLE {table} RENAME COLUMN "{col}" TO "{new_name}"'
        self._sqlite_execute_commit_query(query)

    def _select_rows(self, table:str, cols:Union[str,slice,List], where:str, values:Union[str,int,float,slice,np.ndarray,List], exclude:Union[str,List,None]=None) -> pd.DataFrame:
        """
        Select a given number of rows from a given table.

        Parameters
        ----------
        table: str
            Name of existing table.
        cols: str, slice, list
            Which columns to be included in the selected rows. If string is "*" then all columns will be selected.
        where: str
            Name of column that will be used as reference column to select rows.
        values: str, int, float, slice, list, np.ndarray
            Values of reference column that are in the rows to be selected.
        exclude: None, str, list
            One or more columns to exclude when selecting rows. Useful when "*" is passed in the "cols" parameter.

        Returns
        -------
        Returns the rows of the columns specified by the "cols" parameter filtered by the values of reference columns as pandas.DataFrame.
        """
        if exclude is None:
            exclude = []
        elif isinstance(exlude, str):
            exclude = [exclude]

        if isinstance(cols, list):
            cols = np.setdiff1d(np.array(cols), np.array(exclude)).tolist()
            cols = ",".join(utils._sanitize_column_names(cols))
        elif isinstance(cols, slice):
            tableCols = self._get_table_column_names(table)
            tableCols = np.setdiff1d(np.array(tableCols), np.array(exclude)).tolist()
            start, end, _ = cols.start, cols.stop, cols.step
            if start is None and end is None:
                cols = ",".join(utils._sanitize_column_names(tableCols))
            else:
                if start is None:
                    cols = ",".join(utils._sanitize_column_names(tableCols[:end]))
                elif end is None:
                    cols = ",".join(utils._sanitize_column_names(tableCols[start:]))
                else:
                    cols = ",".join(utils._sanitize_column_names(tableCols[start:end]))

        if where != "rowid":
            colsToSelectString = f'rowid,"{where}",{cols}'
        else:
            colsToSelectString = f'rowid,{cols}'

        if isinstance(values, str):
            query = f'SELECT {colsToSelectString} FROM {table} WHERE {where} = "{values}"'
        elif isinstance(values, int) or isinstance(values, float):
            query = f'SELECT {colsToSelectString} FROM {table} WHERE {where} = {values}'
        elif isinstance(values, slice):
            start, end, _ = values.start, values.stop, values.step
            if start is None and end is None:
                query = f'SELECT {colsToSelectString} FROM {table}'
            else:
                rowIDS = self._get_table_rowids(table)
                if start is None:
                    start = rowIDS[0]
                if end is None:
                    end = rowIDS[-1]
                else:
                    end -= 1
                query = f'SELECT {colsToSelectString} FROM {table} WHERE {where} BETWEEN {start} AND {end}'
        else:
            values = ",".join(f'"{x}"' for x in values)
            query = f'SELECT {colsToSelectString} FROM {table} WHERE {where} IN ({values})'
        results = self._sqlite_execute_fetch_query(query, fetchall=True)
        df = pd.DataFrame(results, columns=[x.replace('"', '') for x in colsToSelectString.split(",")])
        return df.set_index("rowid")

    def _execute_select_query(self, query) -> pd.DataFrame:
        """Execute a SELECT query"""
        results = self._sqlite_execute_fetch_query(query, fetchall=True)

        pattern = r"(?i)select\s+([\w,\s\*\"]+)\s+from\s+(\w+)\s*"
        match = re.search(pattern, query)

        tableName = match.group(2).strip(" ")

        cols = match.group(1).strip(" ")
        if "," in cols:
            cols = cols.split(",")
            parsedCols = []
            for col in cols:
                col = col.strip(" ")
                if col == "*":
                    parsedCols.extend(self._get_table_column_names(tableName, sanitized=False))
                else:
                    parsedCols.append(col.replace('"', ''))
            df = pd.DataFrame(results, columns=parsedCols)
        else:
            if col == "*":
                cols = self._get_table_column_names(tableName, sanitized=False)
            else:
                cols = [cols.replace('"', '')]
            df = pd.DataFrame(results, columns=cols)
        return df

    def _add_column(self, table:str, col:str, data:Union[pd.Series,np.ndarray,List], where_col:str="rowid", where_values:Union[pd.Series,np.ndarray,List]=None) -> None:
        """
        Adds a new column to an existing table.

        Parameters
        ----------
        table: str
            Name of existing table.
        col: str
            The name of the new column.
        data: pandas.Series, numpy.ndarray, list
            The data of the new column.
        where_col: str
            Name of column whose values will be used as reference for the insertion of new data.
        where_values: pandas.Series, numpy.ndarray, list
            Values of reference column.
        """
        sqlDtype = utils.convert_to_sqlite_dtypes(data)[0]

        if isinstance(where_values, list):
            where_values = np.array(where_values)

        if where_col != "rowid" and not where_values.any():
            raise ValueError("Pass values for WHERE clause if WHERE column is not rowid.")

        if where_col == "rowid":
            rowids = self._get_table_rowids(table)
            data = utils.create_data_array_for_sqlite_query(data, rowids=rowids)
        else:
            data = [(val,row) for val,row in zip(data, where_values)] 

        query = f'ALTER TABLE {table} ADD COLUMN "{col}" {sqlDtype}'
        self._sqlite_execute_commit_query(query)

        query = f'UPDATE {table} SET "{col}" = ? WHERE {where_col} = ?'
        self._sqlite_executemany_commit_query(query, values=data)
        self._update_table_shape(table, ncols=1)

    def _add_multiple_columns(self, table:str, cols:List, data:pd.DataFrame) -> None:
        """
        Add multiple columns to a table.

        Parameters
        ----------
        table: str
            The name of the table to add columns to.
        cols: list
            The columns names to be added to the table.
        data: pd.DataFrame
            Dataframe containing the data to be added.
        """
        coltypes = utils.convert_to_sqlite_dtypes(data)
        cols_n_types = [f'"{x}" {y}' for x,y in zip(cols, coltypes)]

        for item in cols_n_types:
            query = f"ALTER TABLE {table} ADD COLUMN {item}"
            self._sqlite_execute_commit_query(query)
        for i in range(len(data)):
            values = data.iloc[i, :].values
            updates = [f'"{col}" = {value}' for col,value in zip(cols, values)]
            query = f'UPDATE {table} SET {','.join(updates)} WHERE rowid = {i}'
            self._sqlite_execute_commit_query(query)
        self._update_table_shape(table, ncols=len(cols))

    def _update_column(self, table:str, col:str, data:Union[pd.Series, np.ndarray, List]) -> None:
        """
        Update the data of a given column in the table.

        Parameters
        ----------
        table: str
            The name of the table of the column to be updated.
        col: str
            The name of the column in the table.
        data: pd.Series, np.ndarray, list
            The data containing the new values for the column.
        """
        rowids = self._get_table_rowids(table)
        data = utils.create_data_array_for_sqlite_query(data, rowids=rowids)
        query = f'UPDATE {table} SET "{col}" = (?) WHERE rowid = (?)'
        self._sqlite_executemany_commit_query(query, values=data)

    def _update_tables_info(self, table:str, col:str, value:str) -> None:
        """
        Update layer's name, tag or description in tables_info

        Parameters
        ----------
        table: str
            Then name of the layer.
        col: str
            The column to be updated. Possible values, "name", "tab" or "description".
        value: str
            The new value for the updated column.
        """
        query = f'UPDATE tables_info SET "{col}" = (?) WHERE name = (?)'
        self._sqlite_execute_commit_query(query, values=(value, table))

    def _get_from_tables_info(self, table:str, col:str) -> Union[str,List]:
        """
        Get all or specific column from tables_info for layer.

        Parameters
        ----------
        table: str
            The name of the layer in the tables_info.
        col: str
            The columns for layers to be fetched. if col="*" then all columns will be fetched.

        Returns
        -------
            One or more columns from tables_info for a given layer.
        """
        query = f'SELECT {col} FROM tables_info WHERE name="{table}"'
        result = self._sqlite_execute_fetch_query(query, fetchall=False)
        if len(result) == 1:
            result = result[0]
        return result

    def _drop_column(self, table:str, col=str) -> None:
        """
        Delete a given column from table.

        Parameters
        ----------
        table: str
            Name of table that has the column.
        col: str
            Name of column to delete.
        """
        query = f'ALTER TABLE {table} DROP "{col}"'
        self._sqlite_execute_commit_query(query)
        self._update_table_shape(table, ncols=-1)

    def _run_query(self, query:str, fetchdf=False) -> Union[pd.DataFrame, None]:
        """Run an arbritary query."""
        if not fetchdf:
            self._sqlite_execute_commit_query(query)
        else:
            cols = query.split(" ", 1)[1]
            cols = cols.lower().split("from")[0].strip(" ")
            data = self._sqlite_execute_fetch_query(query, fetchall=True)
            df = pd.DataFrame(data, columns=cols)
            return df

