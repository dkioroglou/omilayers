Layers methods
==============

Get layer information
---------------------

To get layer's tag or description:

.. code-block:: python

   omi.layers['foo_layer'].tag
   omi.layers['foo_layer'].info

When adding new layer, ``omilayers`` assigns ``na`` as layer's tag and description. To set this kind of information to a layer:

.. code-block:: python

   omi.layers['foo_layer'].set_tag("data") # tag can be an arbritary string.
   omi.layers['foo_layer'].set_info("This is the updated description.")


Get layer columns
-----------------

.. code-block:: python

   omi.layers['foo_layer'].columns


Load layer data
---------------

To load all columns of layer as ``pandas.DataFrame``

.. code-block:: python

   omi.layers['foo_layer'].to_df()

   # Add layer column as pandas.DataFrame index
   omi.layers['foo_layer'].to_df(index='colA')

To load specific columns of layer as ``pandas.DataFrame``

.. code-block:: python

   omi.layers['foo_layer']['colA']
   omi.layers['foo_layer'][['colA', 'colB']]
   omi.layers['foo_layer'][0] # index of column
   omi.layers['foo_layer'][0:10] # slice of columns indices


Conditional layer data load
---------------------------

To load all or certain columns from layer where column ``colB`` has value ``foo`` it can be done with the following ways:

1. Using the ``.loc`` method:

.. code-block:: python

   omi.layers['foo_layer'].loc[["foo"], ['col1', 'col2'], 'colB']


.. note::
   By default, ``.loc`` searches for values in the ``rowid``. To specify the column where the values will be searched, pass the name of the column as a third argument.

Parse the first three rows for a set of columns

.. code-block:: python

   omi.layers['foo_layer'].loc[[0,1,2], ['col1', 'col2']]


2. Using the ``.query`` method:

.. code-block:: python

   # Select all columns where colB has some value
   omi.layers['foo_layer'].query("colB == 0")
   omi.layers['foo_layer'].query("colB == 'someString'")

   # Select columns colA and colC where colB has some value
   omi.layers['foo_layer'].query("colB == 'someString'", cols=['colA', 'colC'])


3. For more complex queries use the "``.select``" method:

.. code-block:: python

   # cols="*" selects all columns
   omi.layers['foo_layer'].select(cols="*", where="colB", values=0)
   omi.layers['foo_layer'].select(cols="*", where="colB", values="string")
   omi.layers['foo_layer'].select(cols="*", where="colB", values=[1,2,3,4])
   omi.layers['foo_layer'].select(cols="*", where="colB", values=np.arange(1,10))

   # To exclude a column from selection
   omi.layers['foo_layer'].select(cols="*", exclude="colC", where="colB", values=np.arange(1,10))
   omi.layers['foo_layer'].select(cols="*", exclude=["colC", "colD"], where="colB", values=np.arange(1,10))

   # To select specific columns
   omi.layers['foo_layer'].select(cols="colC", where="colB", values=np.arange(1,10))
   omi.layers['foo_layer'].select(cols=["colC", "colD"], where="colB", values=np.arange(1,10))


Add or update layer column data
--------------------------------

The code below:

.. code-block:: python

   data = np.arange(1,10)
   data = pd.Series(np.arange(1,10))
   data = [1,2,3,4,5,6,7,8,10]
   omi.layers['foo_layer']['colA'] = data

will add ``colA`` to layer ``foo_layer`` if ``colA`` does not exist. Otherwise, it will replace the data ``colA`` holds.


Rename layer column
-------------------

To rename layer's column name from ``colA`` to ``colB``:

.. code-block:: python

   omi.layers['foo_layer'].rename(col="colA", new_name="colB")


Delete layer column or rows
---------------------------

To delete the entire column ``colA`` from layer:

.. code-block:: python

   omi.layers['foo_layer'].drop("colA")

To delete rows where ``colA`` has certain value(s):

.. code-block:: python

   omi.layers['foo_layer'].drop("colA", values=0)
   omi.layers['foo_layer'].drop("colA", values="string")
   omi.layers['foo_layer'].drop("colA", values=[1,2,3,4])

To delete rows based on their rowids:

.. code-block:: python

   omi.layers['foo_layer'].drop(values=0)
   omi.layers['foo_layer'].drop(values=[0,1,2,3])

.. note::
   When deleting rowids, the ``values`` should be integers.


Replace all layer data
----------------------

To replace the data of a layer:

.. code-block:: python

   new_data = pd.DataFrame({"col1":[1,2,3,4], "col2":[10,20,30.40]})
   omi.layers['foo_layer'].set_data("new_data") # Note that pandas.DataFrame is passed as string.


Insert rows to layer
--------------------

To insert new rows to an existing layer it can be done with two ways:

1. using a dictionary

.. code-block:: python

   data = {"col1":[1,2,3,4], "col2":[10,20,30,40]}
   omi.layers['foo_layer'].insert(data)

.. note::
   The names of the dictionary's keys should match column names in the layer.

2. using a ``pandas.DataFrame``

.. code-block:: python

   data = pd.DataFrame({"col1":[1,2,3,4], "col2":[10,20,30.40]})

   # Column order in data does not match order in layer.
   omi.layers['foo_layer'].insert(data)

   # Column order in data matches order in layer.
   omi.layers['foo_layer'].insert(data, ordered=True)


Create json with layer columns
------------------------------

To create a python dictionary with keys the values of column ``colA`` and values the values of column ``colB`` of a layer:

.. code-block:: python

   omi.layers['foo_layer'].to_json(key_col="colA", value_col="colB")



