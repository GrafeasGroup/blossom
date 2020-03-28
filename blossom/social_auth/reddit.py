from social_core.backends.oauth import BaseOAuth2
from urllib.parse import urlencode

# This is able to start the oauth process but then fails with a 422 error
# from Reddit after authorizing from the user's account. More debugging
# is needed and this should not be considered complete.


class RedditOAuth2(BaseOAuth2):
    """
    Reddit OAuth2 backend
    """

    name = "reddit"
    AUTHORIZATION_URL = "https://www.reddit.com/api/v1/authorize"
    ACCESS_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    REFRESH_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    REDIRECT_STATE = False
    SCOPE_SEPARATOR = ","
    SEND_USER_AGENT = True
    EXTRA_DATA = [("client_id", "client_id"), ("expires", "expires")]

    def get_scope(self):
        # https://python-social-auth-docs.readthedocs.io/en/latest/use_cases.html#multiple-scopes-per-provider
        scope = super().get_scope()
        # See above link for why this is not scope += [()]
        scope = scope + ["identity"]
        return scope

    def get_user_details(self, response):
        """Return user details from GitHub account"""
        breakpoint()
        return {
            "username": response.get("login"),
            "email": response.get("email") or "",
            "first_name": response.get("name"),
        }

    def user_data(self, access_token, *args, **kwargs):
        """Loads user data from service"""
        url = "https://api.github.com/user?" + urlencode({"access_token": access_token})
        return self.get_json(url)
