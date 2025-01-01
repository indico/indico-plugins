# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import difflib
import errno
import os
import sys
from collections import defaultdict
from pathlib import Path

import click
import tomlkit
import yaml
from packaging.version import Version
from pygments import highlight
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.lexers.diff import DiffLexer


START_MARKER = '# BEGIN GENERATED REQUIREMENTS'
END_MARKER = '# END GENERATED REQUIREMENTS'


def _find_plugins():
    subdirs = sorted(Path(x) for x in next(os.walk('.'))[1]
                     if x[0] != '.' and x != '_meta' and os.path.exists(os.path.join(x, 'pyproject.toml')))
    for subdir in subdirs:
        path = subdir / 'pyproject.toml'
        data = tomlkit.parse(path.read_text())
        name = data['project']['name']
        version = data['project']['version']
        if name is None or version is None:
            click.secho(f'Could not extract name/version from {path}', fg='red', bold=True)
            continue
        minver = str(Version(version))
        yield name, minver


def _get_config():
    rv = {'extras': {}, 'skip': []}
    try:
        f = open('_meta/meta.yaml')  # noqa: SIM115
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            raise
    else:
        with f:
            rv.update(yaml.safe_load(f))
    return rv


def _show_diff(old, new, filename):
    diff = difflib.unified_diff(old.splitlines(), new.splitlines(), filename, filename, lineterm='')
    diff = '\n'.join(diff)
    print(highlight(diff, DiffLexer(), Terminal256Formatter(style='native')))


def _update_meta(pyproject: Path, data):
    content = pyproject.read_text()
    new_content = tomlkit.dumps(data)
    if content == new_content:
        return False
    _show_diff(content, new_content, pyproject.name)
    pyproject.write_text(new_content)
    return True


@click.command()
@click.argument('nextver')
def cli(nextver):
    if not os.path.isdir('_meta/'):
        click.secho('Could not find meta package (_meta subdir)', fg='red', bold=True)
        sys.exit(1)

    nextver = Version(nextver)
    if nextver.dev is None:
        nextver = Version(str(nextver) + '-dev')

    config = _get_config()
    plugins_require = []
    extras_require = defaultdict(list)
    for name, minver in sorted(_find_plugins()):
        if name in config['skip']:
            continue
        pkgspec = f'{name}>={minver},<{nextver}'
        if name in config['extras']:
            extras_require[config['extras'][name]].append(pkgspec)
        else:
            plugins_require.append(pkgspec)

    pyproject = Path('_meta/pyproject.toml')
    data = tomlkit.parse(pyproject.read_text())
    data['project']['dependencies'] = [
        *(x for x in data['project']['dependencies'] if not x.startswith('indico-plugin-')),
        *(tomlkit.string(name, literal=True) for name in plugins_require)
    ]
    data['project']['dependencies'].multiline(True)

    if extras_require:
        optional_deps = tomlkit.table()
        for extra, pkgspecs in sorted(extras_require.items()):
            optional_deps[extra] = tomlkit.array(sorted(tomlkit.string(x, literal=True) for x in pkgspecs))
        data['project']['optional-dependencies'] = optional_deps
    else:
        data['project'].pop('optional-dependencies', None)

    if _update_meta(pyproject, data):
        click.secho('Updated meta package', fg='green')
    else:
        click.secho('Meta package already up to date', fg='yellow')


if __name__ == '__main__':
    cli()
