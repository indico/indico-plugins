Plugin Configuration
====================

The plugin must be installed for an entire Indico instance.
It can be enabled and configured for the entire instance and per individual event.
Both levels have the same configuration options:
The global settings act as a default, and are overridden by event specific settings.

Configuration Options
---------------------

**SixPay Saferpay URL**

    The URL to contact the Six Payment Service.
    Use the default ``https://www.saferpay.com/hosting/`` for any transaction.
    For testing, use the ``https://test.saferpay.com/hosting/`` test service.

    You should generally *not* change this, unless you want to test the plugin.
    If the official saferpay URL changes, please submit an `issue ticket`_.

**Account ID**

  The ID of your Saferpay account, a number containing slashes.
  For testing, use the ID ``401860-17795278``.

  This ID is provided to you by Six Payment Services.

**Order Description** [80 characters]

  The description of each order in a human readable way.
  This description is presented to the registrant during the transaction with SixPay.

  This field is limited to 80 characters, after any placeholders are filled in.
  The suggested length is 50 characters.
  The default description uses the registrant name and event title.

**Order Identifier** [80 characters]

  The identifier of each order for further processing.
  This identifier is used internally and in your own billing.

  This field is stripped of whitespace and limited to 80 characters, after any placeholders are filled in.
  Note that auxiliary services, e.g. for billing, may limit this information to 12 characters.

**Notification Mail**

  Mail address to receive notifications of transactions.
  This is independent of Indico's own payment notifications.

Format Placeholders
-------------------

The **Order Description/Identifier** settings allow for placeholders.
These are dynamically filled in for each event and registrant.

``{user_id}`` [`231`]

  Numerical identifier of the user/registrant.
  This is unique per event, but not globally unique.

``{user_name}`` [`Jane Doe`]

  Full name of the user/registrant.
  Use ``<first name> <last name>`` format.

``{user_firstname}`` [`Jane`]

  First name of the user/registrant.

``{user_lastname}`` [`Doe`]

  Last name of the user/registrant.

``{event_id}`` [`18`]

  Numerical identifier of the event.
  This is globally unique.

``{event_title}`` [`My Conference`]

  Full title of the event.

``{eventuser_id}`` [`e18u231`]

  A globally unique identifier for both the event and user.

``{registration_title}`` [`Early Bird`]

  The title of the registration, as shown by Indico.

Placeholders use the `Format String Syntax`_ of Python.
For example, ``{event_title:.6}`` is replaced with the first six characters of the event title.

Note that both fields taking placeholders have a maximum size.
Since a template cannot be validated exactly, size validation assumes a reasonably terse input.
In practice, fields may be silently shortened after formatting with long input.

Placeholder Examples
^^^^^^^^^^^^^^^^^^^^

Below are some examples for use as **Order Description** and **Order Identifier**:

===================================================== ====================================
Format Template                                       Example Output
===================================================== ====================================
   **Order Description**
------------------------------------------------------------------------------------------
``{event_title} (RegNr. {user_id})``                  My Conference (RegNr. 231)
``{event_title}: {user_name} ({registration_title})`` My Conference: Jane Doe (Early Bird)
``{event_title} ({registration_title})``              My Conference (Early Bird)
----------------------------------------------------- ------------------------------------
   **Order Identifier**
------------------------------------------------------------------------------------------
``{eventuser_id}-{user_firstname:.1}{user_lastname}`` e18u231-JDoe
``{event_title:.7} {eventuser_id}``                   My Conf e18u231
===================================================== ====================================


.. _issue ticket: https://github.com/maxfischer2781/indico_sixpay/pulls

.. _Format String Syntax: https://docs.python.org/3/library/string.html#formatstrings
