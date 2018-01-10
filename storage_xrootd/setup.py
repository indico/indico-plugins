# This file is part of Indico.
# Copyright (C) 2002 - 2018 European Organization for Nuclear Research (CERN).
#
# Indico is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.
#
# Indico is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Indico; if not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from setuptools import setup


setup(
    name='indico-plugin-storage-xrootd',
    version='1.0',
    description='XRootD/EOS storage backend for Indico',
    url='https://github.com/indico/indico-plugins',
    license='https://www.gnu.org/licenses/gpl-3.0.txt',
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
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 2.7'
    ],
    entry_points={'indico.plugins': {'storage_xrootd = indico_storage_xrootd:XRootDStoragePlugin'}}
)
