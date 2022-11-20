indico-plugin-payment-stripe
============================

**This fork uses Stripe's checkout instead of the v2 API, allowing it to be SCA-complaint.**

`Stripe <https://stripe.com/>`_ payment support plugin for the `Indico conference management system <https://getindico.io>`_.

This plugin was tested and developed using:

* Indico version 3.2.0
* Stripe API version 2022-11-15. (Stripe Python 5.0.0)
* PostgresSQL
* Redis

Other versions of Indico and/or Stripe may or may not function as intended. We recommend that you test your integration
thoroughly before using this plugin.

See the `Stripe testing documentation <https://stripe.com/docs/testing>`_ for a testing guide.

Requirements
------------

* Python 3.9

Development
-----------

Setup
^^^^^

In general, the following steps can be your guide for setting a local development environment:

.. code-block:: bash

    # Install all requirements
    $ brew install pyenv pyenv-virtualenv postgres redis

    # Clone the repository and cd into it
    $ git clone {repo-url}
    $ cd indico-payment-stripe

    # Create your virtualenv, using pyenv for example (highly recommended: https://github.com/pyenv/pyenv)
    # Besides of pyenv you will need pyenv-virtualenv
    $ pyenv install 3.9
    $ pyenv virtualenv 3.9 indico-plugin-stripe-dev
    $ pyenv activate indico-plugin-stripe-dev

    # From within the root directory and with an active virtualenv, install the dependencies and package itself
    $ pip3 install -e . # To install dev dependencies run `pip3 install -r requirements-dev.txt`

    # Check that everything works by running the tests
    $ tox -i https://pypi.org/simple


License
=======

This plugin is MIT-licensed. Refer to the ``LICENSE`` file for the full license.

Use of the Stripe logo included in this plugin is covered by `Stripe's usage agreement
<https://stripe.com/marks/legal>`_.
