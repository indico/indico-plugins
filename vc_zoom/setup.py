# This file is part of the Indico plugins.
# Copyright (C) 2020 - 2021 CERN and ENEA
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from setuptools import setup


# XXX: keeping some entries in here to make bulk updates easier while
# other plugins still have this metadata in setup.py; everything else
# is in setup.cfg now
setup(
    name='indico-plugin-vc-zoom',
    version='2.3',
    install_requires=[
        'indico>=2.3.4',
        'PyJWT>=1.7.1,<2'
    ],
)
