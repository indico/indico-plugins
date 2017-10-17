Indico Plugins
==============

|build-status|_

This repository contains all the official plugins for `Indico`_.

Indico and its plugins are free software licenced under the terms of the
GNU General Public Licence (GPL) v3.  They are provided on an "as is" basis.

To install a plugin (e.g. "payment_manual"):

.. code-block:: sh

   git clone https://github.com/indico/indico-plugins
   pip install -e indico-plugins/payment_manual

To enable a plugin (e.g. "payment_manual") add it to the plugins list in the indico configuration file "indico.conf" like here:

.. code-block::

   Plugins = {'payment_manual'}

.. |build-status| image:: https://travis-ci.org/indico/indico-plugins.svg?branch=master
                   :alt: Travis Build Status
.. _build-status: https://travis-ci.org/indico/indico-plugins
.. _Indico: https://github.com/indico/indico
