import os
from typing import Dict, Union

import stripe
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv

from blossom.website.models import Post

load_dotenv()

if settings.DEBUG:
    stripe.api_key = os.environ.get("STRIPE_DEBUG_KEY", "sk_test_abcdefghijk")
else:
    stripe.api_key = os.environ.get("STRIPE_PROD_KEY", "sk_live_abcdefghijk")


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
    except (ValueError, TypeError):
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
        success_url=build_url(request, thanks_post),
        cancel_url=build_url(request, donate_post),
    )
    return JsonResponse({"id": session.id})
