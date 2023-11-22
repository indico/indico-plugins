# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2023 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

import errno
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import click
import yaml
from packaging.version import Version
from setuptools.config.setupcfg import read_configuration


START_MARKER = '# BEGIN GENERATED REQUIREMENTS'
END_MARKER = '# END GENERATED REQUIREMENTS'


def _find_plugins():
    subdirs = sorted(Path(x) for x in next(os.walk('.'))[1]
                     if x[0] != '.' and x != '_meta' and os.path.exists(os.path.join(x, 'setup.cfg')))
    for subdir in subdirs:
        path = subdir / 'setup.cfg'
        metadata = read_configuration(path)['metadata']
        name = metadata['name']
        version = metadata['version']
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


def _update_meta(data):
    path = Path('_meta/setup.cfg')
    content = path.read_text()
    new_content = re.sub(fr'(?<={re.escape(START_MARKER)}\n).*(?=\n{re.escape(END_MARKER)})', data, content,
                         flags=re.DOTALL)
    if content == new_content:
        return False
    path.write_text(new_content)
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

    output = [f'    {entry}' for entry in plugins_require]
    if extras_require:
        if output:
            output.append('')
        output.append('[options.extras_require]')
        for extra, pkgspecs in sorted(extras_require.items()):
            output.append(f'{extra} =')
            output.extend(f'    {pkg}' for pkg in sorted(pkgspecs))

    if _update_meta('\n'.join(output)):
        click.secho('Updated meta package', fg='green')
    else:
        click.secho('Meta package already up to date', fg='yellow')


if __name__ == '__main__':
    cli()
