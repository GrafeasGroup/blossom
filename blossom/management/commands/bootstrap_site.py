import logging
import os
from typing import Any

import dotenv
from django.core.management.base import BaseCommand

from blossom.api.models import Source
from blossom.authentication.models import BlossomUser
from blossom.website.models import Post

dotenv.load_dotenv()

logger = logging.getLogger("blossom.management.bootstrap")

ABOUT_PAGE = """
<p>The best way to describe our organization is to start with our mission statement:</p>

<blockquote>
  <p>We provide a framework for crowd-sourcing accessible, text-based content for all Internet users, regardless of disability, access devices, or data restrictions.</p>
</blockquote>

<p>There is a lot of content on the internet that is inaccessible to those with visual restrictions, no data plan, or otherwise an inability to load content. A lot of that content is hidden inside images &mdash; images that a phone with low data cannot load, or assistive screen reading technology cannot interpret. We are pioneering a system for locating this content and passing it to volunteers to create pure text representations so that everyone can access it.</p>

<p>This system, so far, has been deployed on Reddit.com under the subreddit <a href="https://reddit.com/r/TranscribersOfReddit" class="real-link" target="_blank" rel="noreferrer">r/TranscribersOfReddit</a> and features an innovative use of gamification concepts and volunteering to engage users and improve communities. Starting with just two people in April of 2017, over 3000 volunteers have transcribed more than 90,000 pieces of content in the following three years. We currently serve a combined digital population of approximately one million Reddit subscribers.</p>

<p>Our work with <a href="https://reddit.com/r/TranscribersOfReddit" class="real-link" target="_blank" rel="noreferrer">r/TranscribersOfReddit</a> has shown that there is a need for this kind of volunteerism and assistance, so we have elected to form a 501(c)(3) to better organize and serve those in need. The name <em>Grafeas Group, Ltd.</em>, as <em>graf&eacute;as</em>, translated from Greek, means "scribe". We see ourselves as the facilitators of the digital scribes and, as such, will do our best to usher in this new avenue of accessibility.</p>

<p>We bring a global presence to this problem, with board members located in the USA, the UK, and the Netherlands. With our explosive growth since inception, we look forward to truly making a mark on today's digital world.</p>
"""  # noqa: E501

GIVING_PAGE = """
<p>We at Grafeas are passionate about making the world a better place, but we can't do it without your help. Our
    volunteers work diligently around the clock to help us get closer to this goal, but we still have operating
    costs that hard work cannot cover.</p>
<p>Our amazing sponsors help us keep the lights on and we'd love to add you to this list. Our sponsors, both in
    services rendered and monetarily, include:</p>

<ul>
    <li><a href="https://www.bugsnag.com/open-source/" class="real-link" target="_blank"
           rel="noreferrer">Bugsnag</a> &mdash; providing free error catching to our open source projects
    </li>
    <li><a href="https://blog.cloudflare.com/cloudflare-open-source-your-upgrade-is-on-the-house/" class="real-link"
           target="_blank" rel="noreferrer">Cloudflare</a> &mdash; providing a free Pro Plan for our domain
    </li>
    <li><a href="https://www.linode.com/" class="real-link" target="_blank" rel="noreferrer">Linode</a> &mdash;
        providing free hosting for our servers
    </li>
    <li><a href="https://stripe.com/" class="real-link" target="_blank" rel="noreferrer">Stripe</a> &mdash; special
        rates and great service
    </li>
    <li>Patrons who have donated here and through <a href="https://www.patreon.com/grafeasgroup" class="real-link"
                                                     target="_blank" rel="noreferrer">Patreon</a></li>
</ul>

<p>Your donation to the Grafeas Group will help us further our goal of worldwide accessibility on the internet. All
    funding goes towards:</p>

<p>
<ul>
    <li>Upgrading servers</li>
    <li>Community management</li>
    <li>Outreach</li>
    <li>Forging new partnerships</li>
</ul>

<p>
    Every dollar counts! We greatly appreciate every donation that we receive, and we do our level best to
    put donations to the best uses possible. If you have any questions, feel free to contact us at
    <a href="mailto:donations@grafeas.org">donations@grafeas.org</a>.
</p>

<div class="card">
    <div class="card-body shadow">
        <div class="row">
            <div class="col-lg-3">
                <div class="input-group input-group-lg needs-validation mb-3">
                    <span class="input-group-text" id="donationAmountLabel">$</span>
                    <input type="text" id="donationAmount" class="form-control" value="10"
                           aria-label="Amount (to the nearest dollar)" aria-describedby="donationAmountLabel">
                </div>
                <div class="invalid-feedback">
                    Please provide a valid number.
                </div>
            </div>
            <div class="col-lg-9">
                <div class="d-grid">
                    <button class="btn btn-block btn-outline-secondary btn-lg shadow" id="checkout-button">Donate!
                    </button>
                </div>
            </div>
        </div>
        <div class="card-footer">
            <div class="small text-muted">
                Donations are handled through Stripe; any transaction will take place on their site.
                All donations are tax-deductable in the U.S. &mdash; a receipt will be sent to you through
                email from Stripe.
            </div>
        </div>
    </div>
</div>

<script src="https://js.stripe.com/v3/"></script>
<script type="text/javascript">
    // Create an instance of the Stripe object with your publishable API key
    var stripe = Stripe('pk_live_pRSTbdTHvPIh5i1YkXf1cmBG');
    var checkoutButton = document.getElementById('checkout-button');

    checkoutButton.addEventListener('click', function () {
        // Create a new Checkout Session using the server-side endpoint you
        // created in step 3.
        let amountElement = document.getElementById("donationAmount")
        if (amountElement.value.match(/^[1-9]\d*(((,\d{3}){1})?(\.\d{0,2})?)$/) === null) {
            amountElement.classList.add("is-invalid")
            return
        }

        fetch(`/payments/?amount=${amountElement.value}`, {
            method: 'POST',
        })
            .then(function (response) {
                return response.json();
            })
            .then(function (session) {
                return stripe.redirectToCheckout({sessionId: session.id});
            })
            .then(function (result) {
                // If `redirectToCheckout` fails due to a browser or network
                // error, you should display the localized error message to your
                // customer using `error.message`.
                if (result.error) {
                    alert(result.error.message);
                }
            })
            .catch(function (error) {
                console.error('Error:', error);
            });
    });
</script>
"""  # noqa: E501, W605

TOS_PAGE = """
<p>Let's keep this really simple: Usage of content ("Content") produced by or associated with Grafeas Group, Ltd. or any of its projects, including but not limited to Transcribers Of Reddit, indicates acceptance of these terms of service ("Terms").</p>

<p>Content is provided under the <a href="https://creativecommons.org/licenses/by/3.0/" target="_blank" rel="nofollow noopener">Creative Commons v3.0 by Attribution license</a> on an as-is basis, without any warranty, to the fullest extent allowable by law.</p>
"""  # noqa: E501

THANKS_PAGE = """
<p>We know that everyone works hard for their money, and we deeply appreciate your decision to help.</p>

<p>Your donation supports the continued work of the Grafeas Group in our efforts for worldwide internet accessibility. Right now, donations are aimed at expanding our partner relationships and increasing our online presence.</p>

<p>Your donation is tax-deductable; once you donate, your receipt will be emailed to you within 24 hours from our partner, Stripe.</p>

<p>Once again, you have our thanks &mdash; thanks for helping us increase accessibility on the web and thanks for being you.</p>

<p>Cheers,</p>

<p>~ The Staff and Board of Grafeas Group, Ltd.</p>
"""  # noqa: E501


class Command(BaseCommand):
    help = "Creates the default entries required for the site."  # noqa: VNE003

    def create_users(self) -> None:
        """Install all of the default user accounts into the database."""
        if not BlossomUser.objects.filter(username="transcribersofreddit").exists():
            BlossomUser.objects.create_user(
                username="transcribersofreddit",
                email="transcribersofreddit@grafeas.org",
            )
            logger.debug(self.style.SUCCESS("Created user transcribersofreddit"))

        if not BlossomUser.objects.filter(username="transcribot").exists():
            BlossomUser.objects.create_user(
                username="transcribot", email="transcribot@grafeas.org"
            )
            logger.debug(self.style.SUCCESS("Created user transcribot"))

        if not BlossomUser.objects.filter(username="tor_archivist").exists():
            BlossomUser.objects.create_user(
                username="tor_archivist", email="archivist@grafeas.org"
            )
            logger.debug(self.style.SUCCESS("Created user tor_archivist"))

        # First we gotta create a new author, otherwise this whole thing will
        # be for naught
        if not BlossomUser.objects.filter(username="admin").exists():
            BlossomUser.objects.create_superuser(
                username="admin",
                email="blossom@grafeas.org",
                password="asdf",  # change me
            )
            logger.debug(self.style.SUCCESS("Admin user created!"))

    def create_sources(self) -> None:
        """Installs the default Source objects for transcriptions and submissions."""
        sources = ["gamma_plus_one", "reddit", "blossom"]

        for source in sources:
            if not Source.objects.filter(name=source).exists():
                Source.objects.create(name=source)
                logger.debug(self.style.SUCCESS(f"Created source {source}"))

    def create_website_posts(self) -> None:
        """Installs the default posts for the primary grafeas.org blog."""
        slugs = ["about-us", "giving-to-grafeas", "terms-of-service", "thank-you"]
        admin = BlossomUser.objects.get(username="admin")

        if Post.objects.filter(slug__in=slugs).count() == len(slugs):
            logger.debug(self.style.SUCCESS("No articles created; all present."))

        if not Post.objects.filter(slug=slugs[0]).first():
            Post.objects.create(
                title="About Us",
                body=ABOUT_PAGE,
                author=admin,
                published=True,
                standalone_section=True,
                header_order=10,
            )
            logger.debug(self.style.SUCCESS("Wrote about page!"))

        if Post.objects.filter(slug=slugs[1]).exists():
            Post.objects.filter(slug=slugs[1]).delete()

        donation_post = Post.objects.create(
            title="Giving to Grafeas",
            body=GIVING_PAGE,
            author=admin,
            published=True,
            standalone_section=True,
            header_order=20,
        )
        donation_post.body.replace(
            "key: ''", f"key: '{os.environ.get('STRIPE_PROD_KEY')}'"
        )
        donation_post.save()
        logger.debug(self.style.SUCCESS("Wrote donation page!"))

        if not Post.objects.filter(slug=slugs[2]).exists():
            Post.objects.create(
                title="Terms of Service",
                body=TOS_PAGE,
                author=admin,
                published=True,
                standalone_section=False,
                show_in_news_view=False,
            )
            logger.debug(self.style.SUCCESS("Wrote TOS page!"))

        if not Post.objects.filter(slug=slugs[3]).exists():
            Post.objects.create(
                title="Thank You",
                body=THANKS_PAGE,
                author=admin,
                published=True,
                standalone_section=False,
                show_in_news_view=False,
            )
            logger.debug(self.style.SUCCESS("Wrote donation thanks page!"))

    def handle(self, *args: Any, **options: Any) -> None:
        """Set up everything needed in the database for a fresh deploy."""
        self.create_users()
        self.create_sources()
        self.create_website_posts()
