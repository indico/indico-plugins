# This file is part of Indico.
# Copyright (C) 2002 - 2017 European Organization for Nuclear Research (CERN).
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

from setuptools import setup, find_packages


setup(
    name='indico_previewer_jupyter',
    version='0.1',
    url='https://github.com/indico/indico-plugins',
    license='https://www.gnu.org/licenses/gpl-3.0.txt',
    author='Indico Team',
    author_email='indico-team@cern.ch',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'indico>=1.9.10',
        'nbconvert>=4.0.0',
        'functools32'
    ],
    entry_points={'indico.plugins': {'previewer_jupyter = indico_previewer_jupyter:JupyterPreviewerPlugin'}}
)
