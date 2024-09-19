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

    def _sqlite_execute_commit_query(self, query) -> None:
        with contextlib.closing(sqlite3.connect(self.db)) as conn:
            with contextlib.closing(conn.cursor()) as c:
                c.execute(query)
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
        results = self._sqlite_execute_fetch_query(query)
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
        results = self._sqlite_execute_fetch_query(query)
        if results:
            rowids = [res[0] for res in results]
        else:
            rowids = []
        return np.array(rowids)

