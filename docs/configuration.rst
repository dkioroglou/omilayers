Configuration
=============

Regarding DuckDB, ``omilayers`` executes queries in a single-threaded mode by default. To change the number of threads, pass a python dictionary with the corresponding configuration setting of DuckDB:

.. code-block:: python

   omi = Omilayers("dname.duckdb", {"threads":8})

to view the available configuration settings of DuckDB:

.. code-block:: python

   omi.config_settings()




