# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2024 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import sys
from pathlib import Path


def _validate_manifest(plugin_dir: Path):
    pkg_dir = plugin_dir / f'indico_{plugin_dir.name}'
    pkg_file = plugin_dir / f'indico_{plugin_dir.name}.py'
    if not pkg_dir.exists() and pkg_file.exists():
        return True
    data_dirs = [
        sub.name
        for sub in pkg_dir.iterdir()
        if sub.name not in {'__pycache__', 'client'} and sub.is_dir() and not any(sub.glob('*.py'))
    ]
    if not data_dirs:
        return True
    expected_manifest = {f'graft {pkg_dir.name}/{plugin_dir}' for plugin_dir in data_dirs}
    manifest_file = plugin_dir / 'MANIFEST.in'
    if not manifest_file.exists():
        print(f'::error::{plugin_dir.name} has no manifest')
        for line in expected_manifest:
            print(f'::error::manifest entry missing: {line}')
        return False
    manifest_lines = set(manifest_file.read_text().splitlines())
    if missing := (expected_manifest - manifest_lines):
        print(f'::error::{plugin_dir.name} has incomplete manifest')
        for line in missing:
            print(f'::error::manifest entry missing: {line}')
        return False
    return True


def main():
    errors = False
    for plugin_dir in Path().iterdir():
        if not plugin_dir.is_dir() or plugin_dir.name == '_meta' or not (plugin_dir / 'setup.cfg').exists():
            continue
        if not _validate_manifest(plugin_dir):
            errors = True

    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
