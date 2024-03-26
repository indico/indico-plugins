# SIXPay-Saferpay Payment Plugin

This plugin provides a payment option for Indico's payment module using the
SIXPay Saferpay API.

When used, the user will be sent to Saferpay to make the payment, and afterwards
they are automatically sent back to Indico.

## Changelog

### 3.3

- Support (and require) Python 3.12

### 3.2.1

- Support Python 3.11

### 3.2

- Update translations

### 3.1.2

- Fix error after successful payment if background confirmation already happened

### 3.1.1

- Ignore pending transactions once they expired

### 3.1

- Adapt to Indico 3.1 changes

### 3.0

- Initial release for Indico 3.0

## Credits

Originally developed by Max Fischer for Indico 1.2 and 2.x. Updated to use the
latest SIXPay API by Martin Claus. Adapted to Indico 3.0 and Python 3 by the
CERN Indico Team.
