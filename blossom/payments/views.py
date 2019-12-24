import json
from json.decoder import JSONDecodeError
import os

import requests
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv

from blossom.website.models import Post

load_dotenv()

gringotts_name = "Gringotts Bank"
gringotts_img = "https://vignette.wikia.nocookie.net/harrypotter/images/0/07/GringottsLogo.gif/revision/latest?cb=20131206014841"
slack_hook_url = os.environ.get("SLACK_PAYMENT_HOOK")

@csrf_exempt
def charge(request, *args, **kwargs):
    # Set your secret key: remember to change this to your live secret key in production
    # See your keys here: https://dashboard.stripe.com/account/apikeys
    if settings.DEBUG:
        stripe.api_key = os.environ.get('STRIPE_DEBUG_KEY')
    else:
        stripe.api_key = os.environ.get('STRIPE_PROD_KEY')
    # Token is created using Checkout or Elements!

    try:
        token = request.POST['stripeToken']
    except KeyError:
        # Someone probably loaded this in a web browser.
        return HttpResponse("go away")
    charge_amount = request.POST.get('amount')
    stripe_email = request.POST.get('stripeEmail')

    charge = stripe.Charge.create(
        amount=charge_amount,
        currency='usd',
        description='Donation',
        source=token,
    )
    if charge['status'] == 'succeeded':
        json_data = {
            'username': gringotts_name,
            'icon_url': gringotts_img,
            'text': "Hmm? A donation? ${:,.2f}, then. Courtesy of one {}."
                    "".format(int(charge_amount) / 100, stripe_email)
        }
        if settings.DEBUG:
            json_data.update({'channel': '#bottest'})

        requests.post(
            slack_hook_url,
            json=json_data
        )
        thanks = Post.objects.get(slug="thank-you")
        return HttpResponseRedirect(f'{thanks.get_absolute_url()}')
    else:
        json_data = {
            'username': gringotts_name,
            'icon_url': gringotts_img,
            'text': "Something went wrong for {} and their attempted gift of ${:,.2f}. "
                    "Might need looking after.".format(
                stripe_email, int(charge_amount) / 100
            )
        }
        if settings.DEBUG:
            json_data.update({'channel': '#bottest'})
        requests.post(
            slack_hook_url,
            json=json_data
        )
        # todo: make an actual error page that they can land at


@csrf_exempt
def ping(request):
    try:
        request_json = json.loads(request.body)
    except JSONDecodeError:
        return HttpResponse('go away')

    if request_json != {
        os.environ.get("PAYMENT_PING_KEY"):
            os.environ.get("PAYMENT_PING_VALUE")
    }:
        return HttpResponse('go away')

    json_data = {
        'username': gringotts_name,
        'icon_url': gringotts_img,
        'text': "What do you want? Go away!",
    }
    if settings.DEBUG:
        json_data.update({'channel': '#bottest'})
    requests.post(
        slack_hook_url,
        json=json_data
    )
    return JsonResponse({'bah': 'humbug.'})
