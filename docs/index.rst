.. |br| raw:: html

   <br />

Welcome to omilayers documentation!
===================================

.. toctree::
   :maxdepth: 1

   self
   installation
   basic_usage
   configuration
   layers_stack
   layers
   run_query
   api

.. image:: images/omilayers_logo.png
   :width: 400
   :alt: Figure 1
   :align: center

``omilayers`` is a Python data management library. It is suitable for multi-omic data analysis, hence the ``omi`` prefix, that involves the handling of diverse datasets usually referred to as omic layers. ``omilayers`` is based on ``DuckDB`` and provides a high-level interface for frequent and repetitive tasks that involve fast storage, processing and retrieval of data without the need to constantly write SQL queries.

The rationale behind ``omilayer`` is the following:

* User stores **layers** of omic data (tables in SQL lingo).
* User creates new layers by processing and restructuring existing layers.
* User can group layers using **tags**.
* User can store a brief description for each layer.

.. note::
   Although ``omilayers`` was created with multi-omic data in mind, it can be used with any kind of data.


Why omilayers?
==============

Using the Python API provided by ``DuckDB``, the user would need to write the following code to parse a column named ``foo`` from a layer called ``omicdata``:

.. code-block:: python

   import duckdb

   with duckdb.connect("dbname.duckdb") as con:
       result = con.sql("SELECT foo FROM omicdata").fetchdf()

Although the above SQL query is straightfoward, it can become quite tedious task if it needs to be repeated multiple times. Since data analysis involves highly repetitive procedures, a user would need to create functions as a means to abstract the process of writing SQL queries. The aim of ``omilayers`` is to provide this level of abstaction to facilitate bioinformatic data analysis. The ``omilayers`` API resembles the ``pandas`` API and the user needs to write the following code to perform the above task:

.. code-block:: python

   from omilayers import Omilayers

   omi = Omilayers("dbname.duckdb")
   result = omi.layers['omicdata']['foo']

