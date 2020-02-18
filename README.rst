indico-plugin-payment-stripe
============================

**This fork uses Stripe's checkout instead of the v2 API, allowing it to be SCA-complaint.**

`Stripe <https://stripe.com/>`_ payment support plugin for the `Indico conference management system <https://getindico.io>`_.

This plugin was tested and developed using:

* Indico version 2.2.4
* Stripe API version 2020-02-18.

Other versions of Indico and/or Stripe may or may not function as intended. We recommend that you test your integration
thoroughly before using this plugin.

See the `Stripe testing documentation <https://stripe.com/docs/testing>`_ for a testing guide.


Issues
------

Check out our `issue tracker <https://github.com/neicnordic/indico-plugin-stripe/issues>`_ for a complete list of
outstanding issues. We welcome any kind of contributions, from bug reports to pull requests.


Requirements
------------

* Python 2.7


Development
-----------

Setup
^^^^^

In general, the following steps can be your guide for setting a local development environment:

.. code-block:: bash

    # Clone the repository and cd into it
    $ git clone {repo-url}
    $ cd indico-payment-stripe

    # Create your virtualenv, using pyenv for example (highly recommended: https://github.com/pyenv/pyenv)
    $ pyenv virtualenv 2.7.15 indico-plugin-stripe-dev

    # From within the root directory and with an active virtualenv, install the dependencies and package itself
    $ pip install -e .[dev]

    # Check that everything works by running the tests
    $ tox


License
=======

This plugin is MIT-licensed. Refer to the ``LICENSE`` file for the full license.

Use of the Stripe logo included in this plugin is covered by `Stripe's usage agreement
<https://stripe.com/marks/legal>`_.
