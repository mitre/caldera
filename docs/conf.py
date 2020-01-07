import os
import sys
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------

project = 'caldera'
copyright = '2020, The MITRE Corporation'
author = 'The MITRE Corporation'


# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc'
]

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
