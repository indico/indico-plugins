indico-plugin-payment-stripe
============================

This is an Indico plugin for the Stripe payment support.


Requirements
------------

* Python 2.7


Development
-----------

Setup
~~~~~

In general, the following steps can be your guide for setting a local development environment:

.. code-block:: bash

    # Clone the repository and cd into it
    $ git clone {repo-url}
    $ cd indico-payment-stripe

    # Create your virtualenv, using pyenv for example (highly recommended: https://github.com/pyenv/pyenv)
    $ pyenv virtualenv 2.7.15 alq-api-dev

    # From within the root directory and with an active virtualenv, install the dependencies and package itself
    $ pip install -e .[dev]

    # Check that everything works by running the tests
    $ tox


License
=======

See LICENSE.
