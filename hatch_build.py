# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import json
import os
import subprocess
from contextlib import contextmanager
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        if os.environ.get('READTHEDOCS') == 'True' or version == 'editable':
            return
        if translations_dir := next(Path().glob('indico_*/translations/'), None):
            _compile_languages(translations_dir)
            _compile_languages_react(translations_dir)


def _compile_languages(translations_dir: Path):
    from babel.messages.frontend import CompileCatalog
    if not any(translations_dir.glob('**/*.po')):
        return
    cmd = CompileCatalog()
    cmd.directory = translations_dir
    cmd.finalize_options()
    cmd.use_fuzzy = True
    cmd.run()


def _compile_languages_react(translations_dir: Path):
    # we assume a ..../indico/{src,plugins/whatever}/ structure for indico and plugin repos
    indico_root = Path('../../../src/').absolute().resolve()
    if not indico_root.exists() and 'CI' in os.environ:
        indico_root = Path('../../../indico/').absolute().resolve()
    for subdir in translations_dir.absolute().iterdir():
        po_file = subdir / 'LC_MESSAGES' / 'messages-react.po'
        json_file = subdir / 'LC_MESSAGES' / 'messages-react.json'
        if not po_file.exists():
            continue
        with _chdir(indico_root):
            output = subprocess.check_output(['npx', 'react-jsx-i18n', 'compile', po_file], stderr=subprocess.DEVNULL)
        json.loads(output)  # just to be sure the JSON is valid
        json_file.write_bytes(output)


@contextmanager
def _chdir(path: Path):
    old_path = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_path)
