"""Test the available helper classes and their methods."""
from types import SimpleNamespace
from typing import Dict, Set

import pytest
from rest_framework import serializers

from blossom.api.helpers import validate_request


@pytest.mark.parametrize(
    "data,data_params,query,query_params,raises",
    [
        ({"a": "a", "b": "b"}, {"a"}, dict(), set(), False),
        (dict(), set(), {"a": "a", "b": "b"}, {"a"}, False),
        ({"a": "a"}, {"a"}, {"b": "b"}, {"b"}, False),
        (dict(), {"a"}, dict(), set(), True),
        (dict(), set(), dict(), {"a"}, True),
    ],
)
def test_validate_request(
    data: Dict, data_params: Set, query: Dict, query_params: Set, raises: bool
) -> None:
    """
    Test whether the behavior of the validate_request decorator is as documented.

    This is done by creating a simple object with the same fields as a Request
    and passing this to a test function wrapped with the decorator. If an error
    has to be thrown, this is asserted and otherwise it is asserted whether
    only and all required values are passed as kwargs with the correct
    corresponding values.
    """

    @validate_request(query_params=query_params, data_params=data_params)
    def test_function(*args: object, **kwargs: object) -> None:
        assert all(param in kwargs for param in data_params.union(query_params))
        assert all(key in data_params.union(query_params) for key in kwargs.keys())
        assert all(data[param] == kwargs[param] for param in data_params)
        assert all(query[param] == kwargs[param] for param in query_params)

    request = SimpleNamespace(data=data, query_params=query)
    if raises:
        with pytest.raises(serializers.ValidationError):
            test_function(None, request)
    else:
        test_function(None, request)
