from blossom_wiki.middleware import wiki_media_url_rewrite
from unittest.mock import Mock


def test_wiki_media_rewrite():
    request = Mock()
    request.get_host.return_value = "wiki.grafeas.localhost:8000"
    request.path = "/media/img1.jpg"

    response = Mock()
    response.return_value = "Woohoo!"
    result = wiki_media_url_rewrite(response)(request)

    assert result.url == "//grafeas.localhost:8000/media/img1.jpg"


def test_middleware_non_wiki_domain():
    request = Mock()
    request.get_host.return_value = "engineering.grafeas.localhost:8000"
    request.path = "/media/img1.jpg"

    response = Mock()
    response.return_value = "Woohoo!"

    assert wiki_media_url_rewrite(response)(request) == "Woohoo!"


def test_middleware_non_media_url():
    request = Mock()
    request.get_host.return_value = "wiki.grafeas.localhost:8000"
    request.path = "/"

    response = Mock()
    response.return_value = "Woohoo!"

    assert wiki_media_url_rewrite(response)(request) == "Woohoo!"
