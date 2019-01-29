# Set your secret key: remember to change this to your live secret key in production
# See your keys here: https://dashboard.stripe.com/account/apikeys
import stripe
stripe.api_key = "sk_test_KDTWx0nFd1lUQXS7DN9nFPWq"

# Token is created using Checkout or Elements!
# Get the payment token ID submitted by the form:
token = request.form['stripeToken'] # Using Flask
amount = request.form['amount']
currency = request.form['currency']

charge = stripe.Charge.create(
    amount=amount,
    currency=currency,
    description='Conference fee',
    source=token,
)
print charge 