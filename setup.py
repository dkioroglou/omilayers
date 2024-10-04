from setuptools import setup, find_packages
import codecs
import os

def read_file(path):
    with open(path) as contents:
        return contents.read()

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

VERSION = '0.2.1'
DESCRIPTION = 'A SQLite and DuckDB wrapper suitable for bioinformatic analysis of multi-omic data.'
LONG_DESCRIPTION = 'This package wraps the APIs of SQLite and DuckDB and provides a subset of their functionality that is suitable for frequent and repetitive tasks involved in bioinformatic analysis of multi-omic data.'

# Setting up
setup(
    name="omilayers",
    version=VERSION,
    author="Dimitrios Kioroglou",
    author_email="<d.kioroglou@hotmail.com>",
    license="CC-BY-4.0",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=long_description,
    keywords=["duckdb", "omics", "bioinformatics", "data analysis"],
    install_requires=read_file("requirements.txt"),
    packages=find_packages(),
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ],
    zip_safe=False,
)
