from django.core.management.base import BaseCommand

from blossom.website.models import Post
from blossom.authentication.custom_user import BlossomUser

ABOUT_PAGE = """
<p>The best way to describe our organization is to start with our mission statement:</p>

<blockquote>
  <p>We provide a framework for crowd-sourcing accessible, text-based content for all Internet users, regardless of disability, access devices, or data restrictions.</p>
</blockquote>

<p>There is a lot of content on the internet that is inaccessible to those with visual restrictions, no data plan, or otherwise an inability to load content. A lot of that content is hidden inside images &mdash; images that a phone with low data cannot load, or assistive screen reading technology cannot interpret. We are pioneering a system for locating this content and passing it to volunteers to create pure text representations so that everyone can access it.</p>

<p>This system, so far, has been deployed on Reddit.com under the subreddit <%= tor_link(:main) %> and features an innovative use of gamification concepts and volunteering to engage users and improve communities. Starting with just two people in April of 2017, over 1,450 volunteers have transcribed more than 40,000 pieces of content in the following year. We currently serve a combined digital population of approximately one million Reddit subscribers.</p>

<p>Our work with <%= tor_link(:main) %> has shown that there is a need for this kind of volunteerism and assistance, so we have elected to form a 501(c)(3) to better organize and serve those in need. The name <em>Grafeas Group, Ltd.</em>, as <em>graf&eacute;as</em>, translated from Greek, means "scribe". We see ourselves as the facilitators of the digital scribes and, as such, will do our best to usher in this new avenue of accessibility.</p>

<p>We bring a global presence to this problem, with board members located in the USA, the UK, and the Netherlands. With our explosive growth since inception, we look forward to truly making a mark on today's digital world.</p>
"""

GIVING_PAGE = """
<p>We at Grafeas are passionate about making the world a better place, but we can't do it without your help. Our volunteers work diligently around the clock to help us get closer to this goal, but we still have operating costs that hard work cannot cover.</p>
<p>Our amazing sponsors help us keep the lights on and we'd love to add you to this list. Our sponsors, both in services rendered and monetarily, include:</p>

<ul>
  <li><%= link_to 'Bugsnag', 'https://www.bugsnag.com/open-source/' %> &mdash; providing free error catching to our open source projects</li>
  <li><%= link_to 'Cloudflare', 'https://blog.cloudflare.com/cloudflare-open-source-your-upgrade-is-on-the-house/' %> &mdash; providing a free Pro Plan for our domain</li>
  <li><%= link_to 'Linode', 'https://www.linode.com/' %> &mdash; providing free hosting for our servers</li>
  <li><%= link_to 'Stripe', 'https://stripe.com/' %> &mdash; special rates and great service</li>
  <li>Patrons who have donated here and through <%= link_to 'Patreon', 'https://www.patreon.com/grafeasgroup' %></li>
</ul>

<p>Your donation to the Grafeas Group will help us further our goal of worldwide accessibility on the internet. All funding goes towards:</p>

<p>
<ul>
    <li>Upgrading servers</li>
    <li>Community management</li>
    <li>Outreach</li>
    <li>Forging new partnerships</li>
</ul>
</p>

<p>Every dollar counts! We recommend picking the option that's best for you &mdash; if the preset options don't suit your needs, please contact us for more information.</p>

<form id="donations" action="https://payments.grafeas.org/charge" method="POST">
    <div class="grid-x grid-padding-x">
        <div class="cell large-auto medium-auto text-center">
            <input type="button" class="button large rounded bordered shadow primary large-down-expanded" id="ten" value="$10 USD">
        </div>
        <div class="cell large-auto medium-auto text-center">
            <input type="button" class="button large rounded bordered shadow primary large-down-expanded" id="twentyFive" value="25 USD">
        </div>
        <div class="cell large-auto medium-auto text-center">
            <input type="button" class="button large rounded bordered shadow primary large-down-expanded" id="fifty" value="$50 USD">
        </div>
    </div>

    <input type="hidden" id="stripeToken" name="stripeToken" />
    <input type="hidden" id="stripeEmail" name="stripeEmail" />
    <input type="hidden" name="amount" id="donationAmount" value=""/>
</form>

<p>Looking for different amounts? We have <%= link_to 'more options located here.', 'give2.html' %> </p>

<script src="https://checkout.stripe.com/checkout.js"></script>
<script src="https://code.jquery.com/jquery-2.2.4.min.js"></script>
<script>
Array.from(document.querySelectorAll('.stripe-button-el')).forEach(function(el) { el.style.display = 'none'; });

var handler = StripeCheckout.configure({
    key: 'pk_live_pRSTbdTHvPIh5i1YkXf1cmBG',
    token: function(token) {
        // append your token id and email, submit your form
    	$("#stripeToken").val(token.id);
        $("#stripeEmail").val(token.email);
        $("#donations").submit();
    }
  });

  $('#ten').on('click', function(e) {
	$("#donationAmount").val("1000");
	openCheckout("Donation ($10)", 1000);
    e.preventDefault();
  });
  $('#twentyFive').on('click', function(e) {
    $("#donationAmount").val("2500");
    openCheckout("Donation ($25)", 2500);
    e.preventDefault();
  });
  $('#fifty').on('click', function(e) {
    $("#donationAmount").val("5000");
    openCheckout("Donation ($50)", 5000);
    e.preventDefault();
  });

  function openCheckout(description, amount)
  {
    handler.open({
      name: 'Grafeas Group, Ltd.',
      image: '/assets/images/logo.png',
      description: description,
      amount: amount
    });
  }
  // Close Checkout on page navigation
  $(window).on('popstate', function() {
    handler.close();
  });
</script>
"""


class Command(BaseCommand):
    help = 'Creates the default entries required for the site.'

    def handle(self, *args, **options):

        slugs = ['about-us', 'giving-to-grafeas']

        if Post.objects.filter(slug__in=slugs).count() == len(slugs):
            self.stdout.write(
                self.style.SUCCESS('No articles created; all present.')
            )

        # First we gotta create a new author, otherwise this whole thing will be for naught
        if not BlossomUser.objects.filter(username="admin").first():
            BlossomUser.objects.create_superuser(
                username="admin",
                email="the_all_powerful@grafeas.org",
                password="asdf"  # change me
            )
            self.stdout.write(
                self.style.SUCCESS('Admin user created!')
            )

        admin = BlossomUser.objects.get(username="admin")

        if not Post.objects.filter(slug=slugs[0]).first():
            Post.objects.create(
                title="About Us",
                body=ABOUT_PAGE,
                author=admin,
                published=True,
                standalone_section=True,
                header_order=10
            )
            self.stdout.write(
                self.style.SUCCESS('Wrote about page!')
            )

        if not Post.objects.filter(slug=slugs[1]).first():
            Post.objects.create(
                title="Giving to Grafeas",
                body=GIVING_PAGE,
                author=admin,
                published=True,
                standalone_section=True,
                header_order=20
            )
            self.stdout.write(
                self.style.SUCCESS('Wrote donation page!')
            )
