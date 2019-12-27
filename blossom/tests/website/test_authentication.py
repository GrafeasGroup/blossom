import pytest

from blossom.tests.helpers import guy, create_test_user
from blossom.authentication.views import LoginView
from blossom.website.forms import LoginForm
from django_hosts.resolvers import get_host_patterns
from django.urls.exceptions import Resolver404

def test_login_redirect_admin(client):
    resp = client.get('/admin/')
    assert resp.get("Location") == "//grafeas.localhost:8000/login/?next=/admin/"


def test_login_redirect_superadmin(client):
    resp = client.get('/superadmin/')
    # this is the built-in django admin panel login page because it's a pain
    # to replace or modify.
    assert resp.get("Location") == "/superadmin/login/?next=/superadmin/"


def test_login(client):
    user = create_test_user()

    response = client.post(
        '/login/', {
            'email': guy.email,
            'password': guy.password,
        }
    )

    assert response.status_code == 302
    assert response.wsgi_request.user == user
    assert response.wsgi_request.user.is_authenticated


def test_login_bad_password(client):
    user = create_test_user()

    response = client.post(
        '/login/', {
            'email': guy.email,
            'password': 'wrong password'
        }
    )
    assert response.status_code == 302
    assert response.wsgi_request.user.is_anonymous
    assert not response.wsgi_request.user.is_authenticated


def test_login_bad_user_info(client):
    response = client.post(
        '/login/', {
            'email': 'a@a.com',
            'password': 'wrong password'
        }
    )
    assert response.status_code == 302
    assert response.wsgi_request.user.is_anonymous
    assert not response.wsgi_request.user.is_authenticated


def test_logout(client, setup_site):
    # the setup_site fixture just runs the bootstrap management command
    # so `request()` will work
    user = create_test_user()

    client.force_login(user)

    assert client.request().context.get('user').is_authenticated
    client.get('/logout/')
    assert not client.request().context.get('user').is_authenticated


def test_hosts_redirect(client, setup_site):
    user = create_test_user()

    response = client.post(
        '/login/?next=/admin/', {
            'email': guy.email,
            'password': guy.password,
        }, follow=True
    )
    assert response.wsgi_request.path == '/admin/'


def test_hosts_redirect_subdomain(client, setup_site):

    create_test_user()

    # this has to use the long form for HTTP_HOST because it checks a
    # specific condition for the redirect.
    response = client.post(
        'login/?next=http%3A//wiki.grafeas.localhost%3A8000/', {
            'email': guy.email,
            'password': guy.password,
        },
        HTTP_HOST='grafeas.localhost:8000',
    )
    result = LoginView().get_redirect(
        request=response.wsgi_request, hosts=get_host_patterns()
    )
    assert result == '//wiki.grafeas.localhost:8000/'


def test_hosts_redirect_invalid_endpoint(client, setup_site):
    create_test_user()

    response = client.post(
        '/login/?next=/snarfleblat/', {
            'email': guy.email,
            'password': guy.password,
        },
        HTTP_HOST='grafeas.localhost:8000',
    )
    with pytest.raises(Resolver404):
        LoginView().get_redirect(
            request=response.wsgi_request, hosts=get_host_patterns()
        )


def test_login_page_request(client, setup_site):
    response = client.get('/login/')
    assert response.status_code == 200
    assert response.context['form'].__class__ == LoginForm
