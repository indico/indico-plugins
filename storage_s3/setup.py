# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.


from setuptools import find_packages, setup


setup(
    name='indico-plugin-storage-s3',
    version='3.0-dev',
    description='S3 storage backend for Indico',
    url='https://github.com/indico/indico-plugins',
    license='MIT',
    author='Indico Team',
    author_email='indico-team@cern.ch',
    packages=find_packages(),
    zip_safe=False,
    platforms='any',
    install_requires=[
        'indico>=3.0.dev0',
        'boto3>=1.14.30,<2.0',
    ],
    python_requires='~=3.9',
    classifiers=[
        'Environment :: Plugins',
        'Environment :: Web Environment',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.9'
    ],
    entry_points={'indico.plugins': {'storage_s3 = indico_storage_s3.plugin:S3StoragePlugin'}}
)
