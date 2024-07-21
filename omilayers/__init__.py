from os import read
import duckdb
from typing import Union
import pandas as pd
from omilayers.core import Stack
from omilayers.core.dbclass import DButils

class Omilayers:

    def __init__(self, db:str, config:dict={"threads":1}, read_only:bool=False):
        self.config = config
        self.db = db
        self.read_only = read_only
        self._dbutils = DButils(db, config, read_only=read_only)
        self.layers = Stack(db, config, read_only)

    def run(self, query:str, fetchdf=False) -> Union[pd.DataFrame, None]:
        """
        Execute a SQL query.

        Parameters
        ----------
        query: str
            Query to execute.
        fetchdf: bool
            Pass True in cases the query fetches data.

        Returns
        -------
        pandas.DataFrame:
            A pandas dataframe if query fetches data like a 'SELECT' query.
        None:
            Nothing if query does not fetch data like a 'UPDATE' query.

        Examples
        --------
        omi.run("SELECT * from tables_info", fetchdf=True)

        """
        return self._dbutils._run_query(query, fetchdf=fetchdf)


    def config_settings(self) -> pd.DataFrame:
        """Print duckdb config settings"""
        return self._dbutils._get_db_config_settings()
            
