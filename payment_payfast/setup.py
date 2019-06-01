# This file is part of the Indico plugins.
# Copyright (C) 2002 - 2019 CERN
#
# The Indico plugins are free software; you can redistribute
# them and/or modify them under the terms of the MIT License;
# see the LICENSE file for more details.

from __future__ import unicode_literals

from setuptools import find_packages, setup


setup(
    name='indico-plugin-payment-payfast',
    version='0.1',
    description='Payfast payments for Indico event registration fees',
    url='https://github.com/indico/indico-plugins',
    license='MIT',
    author='Inus Scheepers',
    author_email='ischeepers@csir.co.za',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'indico>=2.0'
    ],
    classifiers=[
        'Environment :: Plugins',
        'Environment :: Web Environment',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7'
    ],
    entry_points={'indico.plugins': {'payment_payfast = indico_payment_payfast.plugin:PayfastPaymentPlugin'}}
)
