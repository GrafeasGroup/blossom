import pytest

from blossom.management.commands import bootstrap_site


"""
NOTE TO ANYONE WRITING TESTS: DO NOT MODIFY THE ROOT URLCONF IN ANY TEST

THIS WILL LOCK THE URLCONF FOR ALL TESTS ACROSS THE BOARD AND MAKE YOU SPEND
HOURS CHASING GHOSTS

This includes modifying it both ways:
* @pytest.mark.urls('blossom.urls') <- NO

* def test_thing(settings):
      settings.ROOT_URLCONF = 'blossom.urls' <- DOUBLE NO

The ONLY way to access routes across urlconfs should be done through
django_hosts, like so:

from django_hosts.resolvers import reverse

result = client.get(
    reverse(
        'path_name',
        host={name of subdomain in hosts.py}
    ),
    HTTP_HOST={name of subdomain as it would appear in browser}
)

Example:
---

We want to get //api.grafeas.localhost:8000/volunteer. This appears in DRF
as 'volunteer-list', so our three parts of the `get` and `reverse` call look
like this:

1) path name: 'volunteer-list'
2) host: 'api', because that's what the name of the subdomain is in hosts.py.
3) HTTP_HOST: also 'api', but this one is because it's the subdomain you would
    literally type into your browser.

The final call looks like this:

result = client.get(reverse('volunteer-list', host='api'), HTTP_HOST='api')    
"""


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    pass


@pytest.fixture()
def setup_site():
    bootstrap_site.Command().handle()
