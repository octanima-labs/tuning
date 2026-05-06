from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

project = "tuning"
author = "octanima-labs"
copyright = "2026, octanima-labs"
release = "0.1.0"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "sphinx_design",
]

root_doc = "index"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

myst_enable_extensions = ["colon_fence"]

autodoc_class_signature = "separated"
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_typehints_format = "short"
napoleon_google_docstring = True
napoleon_numpy_docstring = False

html_theme = "pydata_sphinx_theme"
html_title = "tuning"
html_logo = "icon.png"
html_favicon = "_static/favicons/favicon.ico"
html_baseurl = "https://octanima-labs.github.io/tuning/"
html_theme_options = {
    "github_url": "https://github.com/octanima-labs/tuning",
    "show_toc_level": 2,
}
html_static_path = ["_static"]
templates_path = ["_templates"]
