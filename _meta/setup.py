# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2020 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from setuptools import setup


# Do not modify this block manually - use `update-meta.py` instead!
# BEGIN GENERATED REQUIREMENTS
plugins_require = [
    'indico-plugin-livesync>=2.3,<2.4.dev0',
    'indico-plugin-payment-manual>=1.0.1,<2.4.dev0',
    'indico-plugin-payment-paypal>=2.2,<2.4.dev0',
    'indico-plugin-piwik>=2.3,<2.4.dev0',
    'indico-plugin-previewer-code>=1.0,<2.4.dev0',
    'indico-plugin-previewer-jupyter>=1.0,<2.4.dev0',
    'indico-plugin-storage-s3>=2.3,<2.4.dev0',
    'indico-plugin-ursh>=2.3,<2.4.dev0',
    'indico-plugin-vc-vidyo>=2.3,<2.4.dev0',
]
extras_require = {}
# END GENERATED REQUIREMENTS


setup(
    name='indico-plugins',
    version='3.0-dev',
    description='A meta-package containing the official Indico plugins',
    url='https://github.com/indico/indico-plugins',
    license='MIT',
    author='Indico Team',
    author_email='indico-team@cern.ch',
    zip_safe=False,
    install_requires=['indico>=3.0.dev0', *plugins_require],
    python_requires='~=3.9',
    extras_require=extras_require,
    classifiers=[
        'Environment :: Plugins',
        'Environment :: Web Environment',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.9',
    ]
)
