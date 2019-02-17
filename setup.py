#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from setuptools import find_packages, setup

from indico_payment_stripe import __author__, __homepage__, __version__


with open('README.rst') as src:
    readme = src.read()
with open('CHANGELOG.rst') as src:
    changelog = src.read().replace('.. :changelog:', '')

with open('requirements.txt') as src:
    requirements = [line.strip() for line in src]
with open('requirements-dev.txt') as src:
    test_requirements = [line.strip() for line in src]

setup(
    name='indico-plugin-payment-stripe',
    version=__version__,
    description=(
        'Stripe payment support plugin for the Indico conference management'
        ' system.'
    ),
    long_description=readme + '\n\n' + changelog,
    long_description_content_type='text/x-rst',
    url=__homepage__,
    license='MIT',
    author=__author__,
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=requirements,
    extras_require={'dev': test_requirements},
    classifiers=[
        'Environment :: Plugins',
        'Environment :: Web Environment',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7'
    ],
    entry_points={
        'indico.plugins': {
            'payment_stripe = indico_payment_stripe.plugin:StripePaymentPlugin'
        }
    }
)
