# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2025 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

# XXX: This module is not as unused as it may appear. It can be referenced in
# the `indico event import-files` command when all files are on S3 and one wants
# to do a fast copy using rclone

import subprocess
import sys

import click

from indico.core.storage.backend import Storage, get_storage
from indico.util.console import verbose_iterator

from indico_storage_s3.storage import S3StorageBase


def copy_files(mapping, backends):
    target_backend_names = list({x[1][0] for x in mapping})
    assert len(target_backend_names) == 1
    target_backend: Storage = get_storage(target_backend_names[0])
    click.echo(f'Target backend: {target_backend_names[0]} ({target_backend.name})')
    if not isinstance(target_backend, S3StorageBase):
        click.echo('Target backend is not S3; aborting')
        sys.exit(1)
    if not all(isinstance(x, S3StorageBase) for x in backends.values()):
        click.echo('Not all source backends are S3; aborting')
        sys.exit(1)
    rclone_remote_name = click.prompt('rclone remote name')
    mapping.sort()
    iterator = verbose_iterator(mapping, len(mapping), get_title=lambda x: x[1][1], print_every=1,
                                print_total_time=True)
    for (source_backend_name, source_file_id), (__, target_file_id) in iterator:
        source_backend: S3StorageBase = backends[source_backend_name]
        _run_rclone(
            rclone_remote_name,
            '/'.join(source_backend._parse_file_id(source_file_id)),
            '/'.join(target_backend._parse_file_id(target_file_id)),
        )


def _run_rclone(remote, src, dst):
    subprocess.check_call(
        [
            'rclone',
            '--s3-no-check-bucket',
            '--s3-acl=bucket-owner-full-control',
            'copyto',
            f'{remote}:{src}',
            f'{remote}:{dst}',
        ]
    )
