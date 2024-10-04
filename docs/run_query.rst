Run SQL query
=============

To run a SQL query with ``omilayers``:

.. code-block:: python

   query = "SELECT * FROM layer_name"
   omi.run(query)

If the query is a ``SELECT`` query, ``omilayers`` will return the results.

.. note::
   Running direct SQL queries with ``omilayers`` is **not recommended**. The purpose of ``omilayers`` is to be a subset of common queries that are useful for data analysis. The method ``.run`` is implemented for infrequent elaborate queries, but not for complex queries. If the user needs to resort to executing SQL queries, the direct use of the databases APIs is recommended.




