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
        if not isinstance(dfname, str):
            raise ValueError("Dataframe should be a string referring to the name of a pandas.DataFrame object.")

        if self._table_exists(table):
            self._drop_table(table)

        df = globals()[dfname]

        try:
            Nrows, Ncols = df.shape
            query = "INSERT INTO tables_info (name,shape) VALUES (?,?)"
            self._sqlite_execute_commit_query(query, values=(table,f"{Nrows}x{Ncols}"))
        except Exception as error:
            print(error)
            if table in self._select_cols(table='tables_info', cols='name')['name'].values.tolist():
                self._delete_rows(table='tables_info', where_col="name", where_values=table)

        try:
            query = "CREATE TABLE {} ({})".format(table, ",".join(utils._dataframe_dtypes_to_sql_datatypes(dfname)))
            self._sqlite_execute_commit_query(query)

            queryPlaceHolders = utils.create_query_placeholders(df)
            query = f"INSERT INTO {table} {','.join(df.columns)} VALUES {queryPlaceHolders}"
            self._sqlite_executemany_commit_query(query, list(df.to_records(index=False)))
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
            cols = [cols]
        colsString = ','.join(cols)
        if limit is None:
            query = f"SELECT {colsString} FROM {table}"
        else:
            query = f"SELECT {colsString} FROM {table} LIMIT {limit}"
        data = self._sqlite_execute_fetch_query(query, fetchall=True)
        df = pd.DataFrame(data, columns=cols)
        return df.set_index(self._get_table_rowids(table, limit=limit))


    def _get_table_column_names(self, table:str) -> List:
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
        return cols

    def _insert_rows(self, table:str, data:str, ordered:bool=False) -> None:
        """
        Insert one or more rows to table using pandas.DataFrame object.

        Parameters
        ----------
        table: str
            Name of the table to insert rows.
        data: str
            String referring to a pandas.DataFrame object.
        ordered: boolean
            True if the order of the columns in the pandas.DataFrame object matches the order of the column in table. False otherwise.
        """
        if not isinstance(data, str):
            raise ValueError("Data should be a string referring to the name of a pandas.DataFrame object.")

        df = globals()[data]
        if not ordered:
            colsOrder = self._get_table_column_names(table)
            df = df[colsOrder]

        # Update table's shape
        Nrows, Ncols = self._get_table_shape(table)
        Nrows += df.shape[0]
        tableShape = f"{Nrows}x{Ncols}"
        query = f"UPDATE tables_info SET shape='{tableShape}' WHERE name='{table}'"
        self._sqlite_execute_commit_query(query)

        queryPlaceHolders = utils.create_query_placeholders(df)
        query = f"INSERT INTO {table} {','.join(df.columns)} VALUES {queryPlaceHolders}"
        self._sqlite_executemany_commit_query(query, list(df.to_records(index=False)))

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
        query = f"ALTER TABLE {table} RENAME COLUMN '{col}' TO '{new_name}'"
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
            cols = ",".join(cols)
        elif isinstance(cols, slice):
            tableCols = self._get_table_column_names(table)
            tableCols = np.setdiff1d(np.array(tableCols), np.array(exclude)).tolist()
            start, end, _ = cols.start, cols.stop, cols.step
            if start is None and end is None:
                cols = ",".join(tableCols)
            else:
                if start is None:
                    cols = ",".join(tableCols[:end])
                elif end is None:
                    cols = ",".join(tableCols[start:])
                else:
                    cols = ",".join(tableCols[start:end])

        if where != "rowid":
            colsToSelectString = f"SELECT rowid,{where},{cols}"
        else:
            colsToSelectString = f"SELECT rowid,{cols}"

        if isinstance(values, str):
            query = colsToSelectString + f"FROM {table} WHERE {where} = '{values}'"
        elif isinstance(values, int) or isinstance(values, float):
            query = colsToSelectString + f"FROM {table} WHERE {where} = {values}"
        elif isinstance(values, slice):
            start, end, _ = values.start, values.stop, values.step
            if start is None and end is None:
                query = colsToSelectString + f"FROM {table}"
            else:
                rowIDS = self._get_table_rowids(table)
                if start is None:
                    start = rowIDS[0]
                if end is None:
                    end = rowIDS[-1]
                else:
                    end -= 1
                query = colsToSelectString + f"FROM {table} WHERE {where} BETWEEN {start} AND {end}"
        else:
            values = ",".join(f"'{x}'" for x in values)
            query = colsToSelectString + f"FROM {table} WHERE {where} IN ({values})"
        results = self._sqlite_execute_fetch_query(query, fetchall=True)
        df = pd.DataFrame(results, columns=colsToSelectString.split(",")) 
        return df.set_index("rowid")

    def _execute_select_query(self, query) -> pd.DataFrame:
        """Execute a SELECT query"""
        cols = query.split(" ", 1)[1]
        cols = cols.lower().split("from")[0].strip(" ")
        if "," in cols:
            cols = [x.strip(" ") for x in cols.split(",")]
        else:
            cols = [cols]
        result = self._sqlite_execute_fetch_query(query)
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

        query = f"ALTER TABLE {table} ADD COLUMN {col} {sqlDtype}"
        self._sqlite_execute_commit_query(query)

        query = f"UPDATE {table} SET {col} = ? WHERE {where_col} = ?"
        self._sqlite_executemany_commit_query(query, values=data)

