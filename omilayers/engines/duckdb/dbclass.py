from typing import List, Union
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
from omilayers import utils


class DButils:

    def __init__(self, db, config, read_only):
        self.db = db
        self.config = config
        self.read_only = read_only
        if not Path(db).exists():
            self._create_table_for_tables_metadata()

    def _configureDB(self, connection) -> None:
        """Configure duckdb database based on session connection."""
        for key,value in self.config.items():
            if isinstance(value, int) or isinstance(value, float):
                connection.execute(f"SET {key}={value}")
            else:
                connection.execute(f"SET {key}='{value}'")

    def _get_db_config_settings(self) -> pd.DataFrame:
        """Get duckdb configuration settings for session"""
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            return con.sql("SELECT * FROM duckdb_settings()").fetchdf()

    def _create_table_for_tables_metadata(self) -> None:
        """Creates table with name 'tables_info' where layers info will be stored"""
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            query = "CREATE TABLE IF NOT EXISTS tables_info (name VARCHAR PRIMARY KEY, tag VARCHAR, info VARCHAR)"
            con.execute(query)

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
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            result = con.sql(query).fetchnumpy()
        return result['rowid']

    def _create_table_from_pandas(self, table:str, data:pd.DataFrame) -> None:
        """
        Deletes previous created table if exists, creates then new table and inserts new values.

        Parameters
        ----------
        table: pandas.DataFrame
            The name of the table.
        data: pandas.DataFrame
            A pandas.DataFrame object.
        """
        dfLocal = data
        if self._table_exists(table):
            self._drop_table(table)
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            try:
                query = "INSERT INTO tables_info (name) VALUES (?)"
                con.execute(query, [table])
                query = f"CREATE TABLE {table} AS SELECT * FROM 'dfLocal'" 
                con.execute(query)
            except Exception as error:
                print(error)
                if self._table_exists(table):
                    self._drop_table(table)
                if table in self._select_cols(table='tables_info', cols='name')['name'].values.tolist():
                    self._delete_rows(table='tables_info', where_col="name", where_values=table)

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
        dfLocal = data
        if not ordered:
            query = f"INSERT INTO {table} BY NAME SELECT * FROM 'dfLocal'"
        else:
            query = f"INSERT INTO {table} SELECT * FROM 'dfLocal'"
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            con.execute(query)

    def _get_tables_info(self, tag:Union[None,str]=None) -> pd.DataFrame:
        """
        Get info for all tables, or for those in a given group tag.

        Parameters
        ----------
        tag: None, str
            If None, info from all tables will be returned. If str, info from tables that belogn to group tag will be returned.
        """
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            query = "SELECT table_name, estimated_size, column_count FROM duckdb_tables()"
            tmp = con.sql(query).fetchdf()
            tmp = tmp.set_index("table_name")
            tmp['shape'] = [f"{r}x{c}" for r,c in zip(tmp['estimated_size'], tmp['column_count'])]
            tmp = tmp.drop("tables_info") 

            if tag is None:
                query = "SELECT * FROM tables_info"
                _tables = con.sql(query).fetchdf()
            else:
                query = f'SELECT * FROM tables_info WHERE tag="?"'
                _tables = con.sql(query, tag).fetchdf()
            _tables = _tables.set_index("name")

            tmp = tmp.loc[_tables.index, 'shape']
            df = pd.concat([_tables, tmp], axis='columns')
            df = df.reset_index()
            df = df[['name', 'tag', 'shape', 'info']]
        return df

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
        if isinstance(cols, list):
            cols = ','.join(cols)
        if limit is None:
            query = f"SELECT {cols} FROM {table}"
        else:
            query = f"SELECT {cols} FROM {table} LIMIT {limit}"
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            df = con.sql(query).fetchdf()
        return df.set_index(self._get_table_rowids(table, limit=limit))

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
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            query = f"ALTER TABLE {table} RENAME TO {new_name}"
            con.execute(query)

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
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            query = f"ALTER TABLE {table} RENAME {col} TO {new_name}"
            con.execute(query)

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
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            con.execute(query)

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
            excludeString = ' '
        elif isinstance(exlude, str):
            excludeString = f' EXCLUDE ({exclude}) '
        else:
            excludeString = f' EXCLUDE ({",".join(exclude)}) '

        if isinstance(cols, list):
            cols = ",".join(cols)
        elif isinstance(cols, slice):
            tableCols = self._get_table_column_names(table)
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
            query = colsToSelectString + excludeString + f"FROM {table} WHERE {where} = '{values}'"
        elif isinstance(values, int) or isinstance(values, float):
            query = colsToSelectString + excludeString + f"FROM {table} WHERE {where} = {values}"
        elif isinstance(values, slice):
            start, end, _ = values.start, values.stop, values.step
            if start is None and end is None:
                query = colsToSelectString + excludeString + f"FROM {table}"
            else:
                rowIDS = self._get_table_rowids(table)
                if start is None:
                    start = rowIDS[0]
                if end is None:
                    end = rowIDS[-1]
                else:
                    end -= 1
                query = colsToSelectString + excludeString + f"FROM {table} WHERE {where} BETWEEN {start} AND {end}"
        else:
            values = ",".join(f"'{x}'" for x in values)
            query = colsToSelectString + excludeString + f"FROM {table} WHERE {where} IN ({values})"
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            df = con.sql(query).fetchdf()
        return df.set_index("rowid")

    def _execute_select_query(self, query) -> pd.DataFrame:
        """Execute a SELECT query"""
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            df = con.sql(query).fetchdf()
        return df

    # def _add_column(self, table:str, col:str, data:Union[pd.Series,np.ndarray,List], where_col:str="rowid", where_values:Union[pd.Series,np.ndarray,List]=None) -> None:
    #     """
    #     Adds a new column to an existing table.
    #
    #     Parameters
    #     ----------
    #     table: str
    #         Name of existing table.
    #     col: str
    #         The name of the new column.
    #     data: pandas.Series, numpy.ndarray, list
    #         The data of the new column.
    #     where_col: str
    #         Name of column whose values will be used as reference for the insertion of new data.
    #     where_values: pandas.Series, numpy.ndarray, list
    #         Values of reference column.
    #     """
    #     duckdbDtype = utils.convert_to_duckdb_dtypes(data)[0]
    #
    #     if isinstance(where_values, list):
    #         where_values = np.array(where_values)
    #
    #     if where_col != "rowid" and not where_values.any():
    #         raise ValueError("Pass values for WHERE clause if WHERE column is not rowid.")
    #
    #     if where_col == "rowid":
    #         rowids = self._get_table_rowids(table)
    #         data = utils.create_data_array_for_duckdb_query(data, rowids=rowids)
    #     else:
    #         data = [(val,row) for val,row in zip(data, where_values)] 
    #
    #     with duckdb.connect(self.db, read_only=self.read_only) as con:
    #         self._configureDB(con)
    #         query = f"ALTER TABLE {table} ADD COLUMN {col} {duckdbDtype}"
    #         con.execute(query)
    #         query = f"UPDATE {table} SET {col} = ? WHERE {where_col} = ?"
    #         con.executemany(query, data)

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
        duckdbDtype = utils.convert_to_duckdb_dtypes(data)[0]

        if isinstance(where_values, list):
            where_values = np.array(where_values)

        if where_col != "rowid" and not where_values.any():
            raise ValueError("Pass values for WHERE clause if WHERE column is not rowid.")

        if where_col == "rowid":
            rowids = self._get_table_rowids(table)

            tmp_table_data = pd.DataFrame({
                "where_col_vals": rowids,
                "col_vals": data
            })
        else:
            tmp_table_data = pd.DataFrame({
                "where_col_vals": where_values,
                "col_vals": data
            })

        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            query = f"ALTER TABLE {table} ADD COLUMN {col} {duckdbDtype}"
            con.execute(query)

            query = "CREATE TEMPORARY TABLE tmp_table AS SELECT * FROM tmp_table_data"
            con.execute(query)

            query = f"UPDATE {table} SET {col} = tmp_table.col_vals FROM tmp_table WHERE {table}.{where_col} = tmp_table.where_col_vals"
            con.execute(query)

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
        coltypes = utils.convert_to_duckdb_dtypes(data)
        cols_n_types = [f"{x} {y}" for x,y in zip(cols, coltypes)]
        query = ";".join([f"ALTER TABLE {table} ADD COLUMN {x}" for x in cols_n_types])
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            con.execute(query)
        for i in range(len(data)):
            values = data.iloc[i, :].values
            updates = [f"{col} = {value}" for col,value in zip(cols, values)]
            query = f"UPDATE {table} SET {','.join(updates)} WHERE rowid = {i}"
            with duckdb.connect(self.db, read_only=self.read_only) as con:
                self._configureDB(con)
                con.execute(query)

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
        data = utils.create_data_array_for_duckdb_query(data, rowids=rowids)
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            query = f"UPDATE {table} SET {col} = ? WHERE rowid = ?"
            con.executemany(query, data)

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
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            query = f"UPDATE tables_info SET {col} = (?) WHERE name = (?)"
            con.execute(query, [value, table])

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
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            query = f"SELECT {col} FROM tables_info WHERE name='{table}'"
            colValue = con.sql(query).fetchdf()[col].values.tolist()
        if colValue:
            return colValue[0]
        else:
            return colValue

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
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            query = f"ALTER TABLE {table} DROP {col}"
            con.execute(query)

    def _drop_table(self, table:str) -> None: 
        """
        Delete table if it exists.

        Parameters
        ----------
        table: str
            Name of table to delete.
        """
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            query = f"DROP TABLE IF EXISTS {table}"
            con.execute(query)
        self._delete_rows(table="tables_info", where_col="name", where_values=table)

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
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            if tag is None:
                query = f"SELECT name FROM tables_info"
            else:
                query = f"SELECT name FROM tables_info WHERE tag='{tag}'"
            tables = con.sql(query).fetchdf()['name'].values.tolist()
        return tables

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
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            query = f"DESCRIBE {table}"
            cols = con.execute(query).fetchdf()['column_name'].values.tolist()
        return cols

    def _run_query(self, query:str, fetchdf=False) -> Union[pd.DataFrame, None]:
        """Run an arbritary query."""
        with duckdb.connect(self.db, read_only=self.read_only) as con:
            self._configureDB(con)
            if not fetchdf:
                con.execute(query)
            else:
                 return con.sql(query).fetchdf()

