from indico.core.plugins import IndicoPluginBlueprint

from indico_payment_stripe.controllers import RHInitStripePayment, RHStripeSuccess


blueprint = IndicoPluginBlueprint(
    'payment_stripe',
    __name__,
    url_prefix='/event/<int:event_id>/registrations/<int:reg_form_id>/payment/response/stripe',
)

blueprint.add_url_rule('/init', 'init', RHInitStripePayment)
blueprint.add_url_rule('/success', 'success', RHStripeSuccess)
