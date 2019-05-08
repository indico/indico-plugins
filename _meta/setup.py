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


# Do not modify this block manually - use `update-meta.py` instead!
# BEGIN GENERATED REQUIREMENTS
plugins_require = [
    'indico-plugin-chat==2.2-dev',
    'indico-plugin-importer==2.2-dev',
    'indico-plugin-importer-invenio==1.0',
    'indico-plugin-livesync==2.0',
    'indico-plugin-livesync-invenio==1.0',
    'indico-plugin-payment-manual==1.0.1',
    'indico-plugin-payment-paypal==1.0',
    'indico-plugin-piwik==2.2-dev',
    'indico-plugin-previewer-code==1.0',
    'indico-plugin-previewer-jupyter==1.0',
    'indico-plugin-search==2.2-dev',
    'indico-plugin-storage-s3==2.0.3',
    'indico-plugin-vc-vidyo==2.2-dev',
]
extras_require = {
    'xrootd': ['indico-plugin-storage-xrootd==1.0'],
}
# END GENERATED REQUIREMENTS


setup(
    name='indico-plugins',
    version='2.2-dev',
    description='A meta-package containing the official Indico plugins',
    url='https://github.com/indico/indico-plugins',
    license='MIT',
    author='Indico Team',
    author_email='indico-team@cern.ch',
    zip_safe=False,
    install_requires=['indico>=2.2.dev0'] + plugins_require,
    extras_require=extras_require,
    classifiers=[
        'Environment :: Plugins',
        'Environment :: Web Environment',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
    ]
)
