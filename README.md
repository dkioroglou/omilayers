# omilayers

[![Documentation Status](https://readthedocs.org/projects/pip/badge/?version=stable)](https://pip.pypa.io/en/stable/?badge=stable) [![Downloads](https://static.pepy.tech/badge/omilayers)](https://pepy.tech/project/omilayers)

``omilayers`` is a Python data management library. It is suitable for multi-omic data analysis, hence the `omi` prefix, that involves the handling of diverse datasets usually referred to as omic layers. `omilayers` is based on `DuckDB` and provides a high-level interface for frequent and repetitive tasks that involve fast storage, processing and retrieval of data without the need to constantly write SQL queries.

The rationale behind `omilayers` is the following:

* User stores **layers** of omic data (tables in SQL lingo).
* User creates new layers by processing and restructuring existing layers.
* User can group layers using **tags**.
* User can store a brief description for each layer.


## Why omilayers?

Using the Python API provided by `DuckDB`, the user would need to write the following code to parse a column named `foo` from a layer called `omicdata`:

```python
import duckdb

with duckdb.connect("dbname.duckdb") as con:
   result = con.sql("SELECT foo FROM omicdata").fetchdf()
```

Although the above SQL query is straightfoward, it can become quite tedious task if it needs to be repeated multiple times. Since data analysis involves highly repetitive procedures, a user would need to create functions as a means to abstract the process of writing SQL queries. The aim of `omilayers` is to provide this level of abstaction to facilitate bioinformatic data analysis. The `omilayers` API resembles the `pandas` API and the user needs to write the following code to perform the above task:

```python
from omilayers import Omilayers

omi = Omilayers("dbname.duckdb")
result = omi.layers['omicdata']['foo']
```

## Installation

```
pip install omilayers
```


## Testing with synthetic omic data

The directory `synthetic_data` includes a jupyter notebook for testing `omilayers` using synthetic multi-omic data. It also includes the Python script `create_synthetic_vcf/synthesize_vcf.py` that was used to create the synthetic VCF that is hosted in Zenodo [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.12790872.svg)](https://doi.org/10.5281/zenodo.12790872).

The recreation of the synthetic VCF can be done as following:
```bash
for i in {1..22} {X,Y,M};do python synthesize_vcf.py $i;done
```

To join the generated VCFs into a single VCF:
```bash
for i in {1..22} {X,Y,M};do cat chr${i}.vcf >> simulated.vcf;done
```


## Documentation

You can read the full documentation here: [https://omilayers.readthedocs.io](https://omilayers.readthedocs.io/en/latest/)

