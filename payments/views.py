import os
from typing import Dict, Union

import stripe
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv

from website.models import Post

load_dotenv()

if settings.DEBUG:
    stripe.api_key = os.environ.get("STRIPE_DEBUG_KEY", "sk_test_abcdefghijk")
else:
    stripe.api_key = os.environ.get("STRIPE_PROD_KEY", "sk_live_abcdefghijk")


def test_view(request):
    return render(request, "website/partials/payment_test_page.partial")


def build_url(request: HttpRequest, post_obj: Post) -> str:
    """Create a full URL for a Post object for Stripe."""
    http_type = "http://" if settings.DEBUG else "https://"
    return http_type + request.get_host() + post_obj.get_absolute_url()


@csrf_exempt
def charge(
    request: HttpRequest, *args: Dict, **kwargs: Dict
) -> Union[HttpResponse, JsonResponse]:
    """Create session information for Stripe."""
    donate_post = Post.objects.get(slug="giving-to-grafeas")
    thanks_post = Post.objects.get(slug="thank-you")
    donation_amount = request.GET.get("amount")

    try:
        # convert to stripe's stupid method of "1000 == $10.00"
        donation_amount = int(float(donation_amount) * 100)
    except ValueError:
        # somehow we didn't get a number, so force reload the page.
        return HttpResponseRedirect(donate_post.get_absolute_url())

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Donation"},
                    "unit_amount": donation_amount,
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=build_url(request, thanks_post)
        + "?session_id={CHECKOUT_SESSION_ID}",
        # cancel_url=build_url(request, donate_post),
        cancel_url="http://localhost:8000/payments/testing/",
    )

    return JsonResponse({"id": session.id})


# @csrf_exempt
# def charge(request, *args, **kwargs):
#     # Set your secret key: remember to change this to your live secret key in production
#     # See your keys here: https://dashboard.stripe.com/account/apikeys
#     if settings.DEBUG:
#         stripe.api_key = os.environ.get("STRIPE_DEBUG_KEY", "sk_test_abcdefghijk")
#     else:
#         stripe.api_key = os.environ.get("STRIPE_PROD_KEY", "sk_live_abcdefghijk")
#     # Token is created using Checkout or Elements!
#
#     try:
#         token = request.POST["stripeToken"]
#     except KeyError:
#         # Someone probably loaded this in a web browser.
#         return HttpResponse("go away")
#     charge_amount = request.POST.get("amount")
#     stripe_email = request.POST.get("stripeEmail")
#
#     charge = stripe.Charge.create(
#         amount=charge_amount, currency="usd", description="Donation", source=token,
#     )
#     if charge["status"] == "succeeded":
#         json_data = {
#             "username": gringotts_name,
#             "icon_url": gringotts_img,
#             "text": "Hmm? A donation? ${:,.2f}, then. Courtesy of one {}."
#             "".format(int(charge_amount) / 100, stripe_email),
#         }
#         if settings.DEBUG:
#             json_data.update({"channel": "#bottest"})
#
#         if settings.ENABLE_SLACK:
#             requests.post(slack_hook_url, json=json_data)
#         thanks = Post.objects.get(slug="thank-you")
#         return HttpResponseRedirect(f"{thanks.get_absolute_url()}")
#     else:
#         json_data = {
#             "username": gringotts_name,
#             "icon_url": gringotts_img,
#             "text": "Something went wrong for {} and their attempted gift of ${:,.2f}. "
#             "Might need looking after.".format(stripe_email, int(charge_amount) / 100),
#         }
#         if settings.DEBUG:
#             json_data.update({"channel": "#bottest"})
#
#         if settings.ENABLE_SLACK:
#             requests.post(slack_hook_url, json=json_data)
#         # todo: make an actual error page that they can land at
