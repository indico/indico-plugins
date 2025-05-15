# Stripe Payment Plugin

This plugin provides a payment option for Indico's payment module using [Stripe][stripe].

When used, the user will be sent to Stripe to make the payment, and afterwards
they are automatically sent back to Indico.

See the [Stripe testing documentation][stripe-testing] for a testing guide.

## Configuration

If you want to use the same Stripe API key for the whole Indico instance, you can set it globally in
the plugin settings. Event managers will be able to use it, but they will not be able to see the
API key.

Alternatively, event managers can set their own Stripe API key when enabling the plugin in their
event. This can also be done when a global API key is set in order to override that key.

## Changelog

### 3.3

- Initial release for Indico 3.3
- **Important:** This release is a breaking change; you need to configure your Stripe API key again.
- Stripe API version: `2025-04-30.basil`

## Credits

Originally developed and updated by Wibowo Arindrarto, Dmytro Karpenko, Bernard Kolobara,
Claudio Wunder and other contributors.

Adapted to Indico 3.3 by the CERN Indico Team.

Use of the Stripe logo included in this plugin is covered by [Stripe's usage agreement][stripe-terms].


[stripe]: https://stripe.com
[stripe-testing]: https://stripe.com/docs/testing
[stripe-terms]: https://stripe.com/marks/legal
