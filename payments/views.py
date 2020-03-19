import os

import requests
import stripe
from django.conf import settings
from django.shortcuts import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv

from website.models import Post

load_dotenv()

gringotts_name = "Gringotts Bank"
gringotts_img = "https://vignette.wikia.nocookie.net/harrypotter/images/0/07/GringottsLogo.gif/revision/latest?cb=20131206014841"
slack_hook_url = os.environ.get("SLACK_HOOK")


@csrf_exempt
def charge(request, *args, **kwargs):
    # Set your secret key: remember to change this to your live secret key in production
    # See your keys here: https://dashboard.stripe.com/account/apikeys
    if settings.DEBUG:
        stripe.api_key = os.environ.get("STRIPE_DEBUG_KEY", "sk_test_abcdefghijk")
    else:
        stripe.api_key = os.environ.get("STRIPE_PROD_KEY", "sk_live_abcdefghijk")
    # Token is created using Checkout or Elements!

    try:
        token = request.POST["stripeToken"]
    except KeyError:
        # Someone probably loaded this in a web browser.
        return HttpResponse("go away")
    charge_amount = request.POST.get("amount")
    stripe_email = request.POST.get("stripeEmail")

    charge = stripe.Charge.create(
        amount=charge_amount, currency="usd", description="Donation", source=token,
    )
    if charge["status"] == "succeeded":
        json_data = {
            "username": gringotts_name,
            "icon_url": gringotts_img,
            "text": "Hmm? A donation? ${:,.2f}, then. Courtesy of one {}."
            "".format(int(charge_amount) / 100, stripe_email),
        }
        if settings.DEBUG:
            json_data.update({"channel": "#bottest"})

        if settings.ENABLE_SLACK:
            requests.post(slack_hook_url, json=json_data)
        thanks = Post.objects.get(slug="thank-you")
        return HttpResponseRedirect(f"{thanks.get_absolute_url()}")
    else:
        json_data = {
            "username": gringotts_name,
            "icon_url": gringotts_img,
            "text": "Something went wrong for {} and their attempted gift of ${:,.2f}. "
            "Might need looking after.".format(stripe_email, int(charge_amount) / 100),
        }
        if settings.DEBUG:
            json_data.update({"channel": "#bottest"})

        if settings.ENABLE_SLACK:
            requests.post(slack_hook_url, json=json_data)
        # todo: make an actual error page that they can land at