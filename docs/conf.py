# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
from datetime import datetime

author = "tadams42"
project = "flask-marshmallow-openapi"
copyright = (
    ", ".join(str(y) for y in range(2023, datetime.now().year + 1)) + ", " + author
)
release = "0.6.1"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "myst_parser",
    "sphinx_copybutton",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

intersphinx_mapping = {
    "python": ("https://docs.python.org/3.9", None),
    "marshmallow": ("https://marshmallow.readthedocs.io/en/3.0/", None),
    "json": ("https://simplejson.readthedocs.io/en/latest/", None),
    "simplejson": ("https://simplejson.readthedocs.io/en/latest/", None),
}

add_module_names = False


# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
