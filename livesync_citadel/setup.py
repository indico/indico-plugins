# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from setuptools import find_packages, setup


setup(
    name='indico-plugin-livesync-citadel',
    version='1.0',
    url='https://github.com/indico/indico-plugins',
    license='MIT',
    author='Indico Team',
    author_email='indico-team@cern.ch',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'indico>=3.0-dev',
        'indico-plugin-livesync>=1.0',
        'tika>=1.24'
    ],
    entry_points={
        'indico.plugins': {'livesync_citadel = indico_livesync_citadel.plugin:LiveSyncCitadelPlugin'}
    },
    classifiers=[
        'Environment :: Plugins',
        'Environment :: Web Environment',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.9'
    ],
)
