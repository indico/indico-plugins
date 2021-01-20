# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2021 CERN
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
    install_requires=['indico>=3.0.dev0', *plugins_require],
    extras_require=extras_require,
)
