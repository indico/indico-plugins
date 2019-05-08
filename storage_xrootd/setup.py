# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from setuptools import setup


setup(
    name='indico-plugin-storage-xrootd',
    version='1.0',
    description='XRootD/EOS storage backend for Indico',
    url='https://github.com/indico/indico-plugins',
    license='MIT',
    author='Indico Team',
    author_email='indico-team@cern.ch',
    py_modules=('indico_storage_xrootd',),
    zip_safe=False,
    platforms='any',
    install_requires=[
        'indico>=2.0',
        'xrootdpyfs==0.1.5',
    ],
    classifiers=[
        'Environment :: Plugins',
        'Environment :: Web Environment',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7'
    ],
    entry_points={'indico.plugins': {'storage_xrootd = indico_storage_xrootd:XRootDStoragePlugin'}}
)
