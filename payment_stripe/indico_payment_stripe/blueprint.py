from indico.core.plugins import IndicoPluginBlueprint

from indico_payment_stripe.controllers import RHStripe


blueprint = IndicoPluginBlueprint(
    'payment_stripe',
    __name__,
    url_prefix=(
        '/event/<int:event_id>/registrations/'
        '<int:reg_form_id>/payment/response/stripe'
    )
)

blueprint.add_url_rule('/handler', 'handler', RHStripe, methods=['GET'])
