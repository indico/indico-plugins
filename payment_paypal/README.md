# PayPal Payment Plugin

This plugin provides a PayPal payment option for Indico's payment module.

When used, the user will be sent to PayPal to make the payment, and afterwards
they are automatically sent back to Indico. It relies on PayPal's IPN payment
notification for Indico to automatically mark the registrant as paid once the
payment has been made and processed by PayPal.


## Changelog

### 3.0

- Initial release for Indico 3.0
