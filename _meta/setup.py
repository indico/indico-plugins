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

from setuptools import setup


# Do not modify this block manually - use `update-meta.py` instead!
# BEGIN GENERATED REQUIREMENTS
plugins_require = [
    'indico_chat==1.0.dev0',
    'indico_importer==1.0.dev0',
    'indico_importer_invenio==1.0.dev0',
    'indico_livesync==1.0.dev0',
    'indico_livesync_debug==1.0.dev0',
    'indico_livesync_invenio==1.0.dev0',
    'indico_payment_manual==1.0.dev0',
    'indico_payment_paypal==1.0.dev0',
    'indico_piwik==1.0.dev1',
    'indico_previewer_code==1.0.dev0',
    'indico_previewer_jupyter==1.0.dev0',
    'indico_search==1.0.dev0',
    'indico_search_invenio==1.0.dev0',
    'indico_vc_dummy==1.0.dev0',
    'indico_vc_vidyo==1.0.dev0',
]
extras_require = {
    'xrootd': ['indico_storage_xrootd==1.0.dev0'],
}
# END GENERATED REQUIREMENTS


setup(
    name='indico-plugins',
    version='1.0.dev0',
    url='https://github.com/indico/indico-plugins',
    license='https://www.gnu.org/licenses/gpl-3.0.txt',
    author='Indico Team',
    author_email='indico-team@cern.ch',
    zip_safe=False,
    install_requires=['indico>=2.0.dev1'] + plugins_require,
    extras_require=extras_require,
    classifiers=[
        'Environment :: Plugins',
        'Environment :: Web Environment',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 2.7',
    ]
)
