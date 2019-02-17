# -*- coding: utf-8 -*-
"""
    indico_payment_stripe
    ~~~~~~~~~~~~~~~~~~~~~

    Indico plugin for Stripe payment support.

    :license: MIT

"""

RELEASE = False


__version_info__ = ('0', '0', '1')
__version__ = '.'.join(__version_info__)
__version__ += '-dev' if not RELEASE else ''

__author__ = 'NeIC'
__homepage__ = 'https://github.com/neicnordic/indico-plugin-stripe'
