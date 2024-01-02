# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

"""
This preprocessor marks cells' metadata so that the appropriate highlighter can be used in the `highlight` filter.

More precisely, the language of a cell is set to C++ in two scenarios:
  - Python notebooks: cells with `%%cpp` or `%%dcl` magic extensions.
  - ROOT prompt C++ notebooks: all cells.
This preprocessor relies on the metadata section of the notebook to find out about the notebook's language.

Code courtesy of the ROOT project (https://root.cern.ch).
"""

import re

from nbconvert.preprocessors.base import Preprocessor


class CppHighlighter(Preprocessor):

    """Detects and tags code cells that use the C++ language."""

    magics = ['%%cpp', '%%dcl']
    cpp = 'cpp'
    python = 'python'

    def __init__(self, config=None, **kw):
        super().__init__(config=config, **kw)

        # Build regular expressions to catch language extensions or switches and choose
        # an adequate pygments lexer
        any_magic = '|'.join(self.magics)
        self.re_magic_language = re.compile(fr'^\s*({any_magic}).*', re.DOTALL)

    def matches(self, source, reg_expr):
        return bool(reg_expr.match(source))

    def _preprocess_cell_python(self, cell, resources, cell_index):
        # Mark %%cpp and %%dcl code cells as cpp
        if cell.cell_type == 'code' and self.matches(cell.source, self.re_magic_language):
            cell['metadata']['magics_language'] = self.cpp

        return cell, resources

    def _preprocess_cell_cpp(self, cell, resources, cell_index):
        # Mark all code cells as cpp
        if cell.cell_type == 'code':
            cell['metadata']['magics_language'] = self.cpp

        return cell, resources

    def preprocess(self, nb, resources):
        self.preprocess_cell = self._preprocess_cell_python
        try:
            if nb.metadata.kernelspec.language == 'c++':
                self.preprocess_cell = self._preprocess_cell_cpp
        except Exception:  # noqa: S110 - no idea what exception's being caught here :(
            # if no language metadata, keep python as default
            pass
        return super().preprocess(nb, resources)
