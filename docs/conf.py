import os
import sys

import sphinx.ext.apidoc as apidoc

sys.path.insert(0, os.path.abspath('..'))

# Call sphinx-apidoc to generate stub files from our source code.
# -o generated: output rst stubs to this directory
# --implicit-namespaces: will find modules in packages without explicit __init__.py
# --force: overwrite existing generated stubs
# ../app/: this is the directory where caldera lives
apidocs_argv = ['-o', '_generated', '--implicit-namespaces', '--force', '../app/']
apidoc.main(apidocs_argv)

# -- Project information -----------------------------------------------------

project = 'caldera'
copyright = '2020, The MITRE Corporation'
author = 'The MITRE Corporation'
master_doc = 'index'


# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'recommonmark',
]

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
