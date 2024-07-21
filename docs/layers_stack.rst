Layers stack methods
====================

View stored layers
------------------

To view all stored layers:

.. code-block:: python

   print(omi.layers)

``omilayers`` will print a table with the following columns:

* **name**: User assigned name to the layer.
* **tag**: User assigned tag to the layer.
* **shape**: Number of rows and columns of layer in the form ``NrowsxNcols``.
* **info**: User assigned description to the layer.

Tags are used as a way to group layers. To view layers with a given tag:

.. code-block:: python

   print(omi.layers("tag_name"))

``omilayers`` will print a table with the following columns:

* **name**: User assigned name to the layer.
* **tag**: User assigned tag to the layer.
* **info**: User assigned description to the layer.

Rename layer
------------

To rename a layer called ``foo_layer`` to ``bar_layer``:

.. code-block:: python

   omi.layers.rename(layer='foo_layer', new_name="bar_layer")


Delete layer
------------

To delete a layer with name ``foo_layer``:

.. code-block:: python

   omi.layers.drop("foo_layer")


Search for layer
----------------

The more layers the user adds, the more difficult it gets to keep track of what kind of data each layer holds. To search for layers that include for instance the term "colA":

.. code-block:: python

   omi.layers.search("colA")

``omilayers`` will search for the term "colA" in the following places:

* The names of the layers.
* The description of the layers.
* The column names of the layers.

After the search is completed, ``omilayers`` prints the names of the layers where the term was found.


