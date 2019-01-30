from __future__ import unicode_literals

from indico.core.plugins import IndicoPluginBlueprint

from indico_payment_stripe.handler import StripeHandler


blueprint = IndicoPluginBlueprint('payment_stripe', __name__)

blueprint.add_url_rule('/handler', 'handler', StripeHandler, methods=('POST'))