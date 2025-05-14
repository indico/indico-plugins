# Stripe Payment Plugin

This plugin provides a payment option for Indico's payment module using [Stripe][stripe].

When used, the user will be sent to Stripe to make the payment, and afterwards
they are automatically sent back to Indico.

This plugin uses the Stripe API version `2022-11-15`.
See the [Stripe testing documentation][stripe-testing] for a testing guide.

## Changelog

### 3.3

- Initial release for Indico 3.3

## Credits

Originally developed and updated by Wibowo Arindrarto, Dmytro Karpenko, Bernard Kolobara,
Claudio Wunder and other contributors.

Adapted to Indico 3.3 by the CERN Indico Team.

Use of the Stripe logo included in this plugin is covered by [Stripe's usage agreement][stripe-terms].


[stripe]: https://stripe.com
[stripe-testing]: https://stripe.com/docs/testing
[stripe-terms]: https://stripe.com/marks/legal
