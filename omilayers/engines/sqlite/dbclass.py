from typing import List, Union
from pathlib import Path
import numpy as np
import pandas as pd
from omilayers import utils
import contextlib
import sqlite3

class DButils:

    def __init__(self, db, config, read_only):
        self.db = db
        self.config = config
        self.read_only = read_only
        if not Path(db).exists():
            self._create_table_for_tables_metadata()

    def _sqlite_execute_commit_query(self, query, values=None) -> None:
        with contextlib.closing(sqlite3.connect(self.db)) as conn:
            with contextlib.closing(conn.cursor()) as c:
                if values is None:
                    c.execute(query)
                else:
                    c.execute(query, values)
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
        query = "CREATE TABLE IF NOT EXISTS tables_info (name TEXT PRIMARY KEY, tag TEXT, info TEXT)"
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
        self._sqlite_execute_commit_query(query)

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

    def _create_table_from_pandas(self, table:str, dfname:str) -> None:
        """
        Deletes previous created table if exists, creates then new table and inserts new values.

        Parameters
        ----------
        table: str
            The name of the table.
        dfname: str
            A string that is referring to a pandas.DataFrame object.
        """
        if self._table_exists(table):
            self._drop_table(table)
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            try:
                query = "INSERT INTO tables_info (name) VALUES (?)"
                self._sqlite_execute_commit_query(query, values=(table,))

                query = "CREATE TABLE {} ({})".format(table, ",".join(utils._dataframe_dtypes_to_sql_datatypes(dfname)))
                self._sqlite_execute_commit_query(query)
            except Exception as error:
                print(error)
                if self._table_exists(table):
                    self._drop_table(table)
                if table in self._select_cols(table='tables_info', cols='name')['name'].values.tolist():
                    self._delete_rows(table='tables_info', where_col="name", where_values=table)

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
            cols = [cols]
        colsString = ','.join(cols)
        if limit is None:
            query = f"SELECT {colsString} FROM {table}"
        else:
            query = f"SELECT {colsString} FROM {table} LIMIT {limit}"
        data = self._sqlite_execute_fetch_query(query, fetchall=True)
        df = pd.DataFrame(data, columns=cols)
        return df.set_index(self._get_table_rowids(table, limit=limit))

