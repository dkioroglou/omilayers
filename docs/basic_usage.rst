Basic usage
============

Add new layer
-------------

To create new layers, the data should be as ``pandas.DataFrame``.

.. code-block:: python

    import pandas as pd
    from omilayers import Omilayers

    omi = Omilayers('some/path/my.duckdb') # database will be created if it doesn't exist.
    df = pd.DataFrame({"col1":[1,2,3,4,5], "col2":[10,20,30,40,50]})
    omi.layers['first_layer'] = "df" # Note that pandas.DataFrame should be passed as string.


To create new layer from a ``csv`` file:

.. code-block:: python

    from omilayers import Omilayers

    omi = Omilayers('some/path/my.duckdb') # database will be created if it doesn't exist.
    omi.layers.from_csv(layer='first_layer', filename='filename.csv', sep='\t')


the ``from_csv`` method takes the same keywords as those defined in ``pandas.read_csv``.


