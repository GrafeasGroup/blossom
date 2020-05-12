from functools import wraps
from typing import Callable, Dict, Set

from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response

from authentication.models import BlossomUser


def _retrieve_keys(data: Dict, keys: Set, name: str) -> Dict[str, str]:
    """
    Retrieve all values from the data with the given keys, creating key-value pairs.

    :param data: the dictionary from which to extract values
    :param keys: the keys required to be in the data and to return the key-value pair for
    :param name: the name of the data dictionary; used if an error is thrown
    :return: the key-value pairs from the dictionary with the specified keys
    :raise ValidationError: when a key is missing from the data
    """
    missing_keys = keys.difference(data.keys())
    if missing_keys:
        raise serializers.ValidationError(
            f"The following keys from {name} are missing : {missing_keys}."
        )
    return {key: data[key] for key in keys}


def validate_request(query_params: Set = None, data_params: Set = None) -> Callable:
    """
    Validate arguments of the Request within inner method.

    This decorator is to be used ONLY around a method which has access to
    a Request object as its first positional argument, as this object is
    validated within the decorator.

    In the parameters query_params and data_params the user can provide a set
    of parameters which the request query and data should contain respectively.

    Note that as of now only the existence of a key within these two
    dictionaries is checked; no further validation is yet done.

    Only the values from the required keys are passed as keyword arguments with the
    respective keys. Note that it is assumed that the query and data parameters
    do not contain equal named parameters, the behavior is undefined otherwise.

    :param query_params: the set of query parameters which should exist in the Request.
    :param data_params: the set of data parameters which should exist in the Request.
    :return: the decorator which wraps this function.
    """
    query_params = set() if query_params is None else query_params
    data_params = set() if data_params is None else data_params

    def decorator(function: Callable) -> Callable:
        @wraps(function)
        def wrapper(
            self: object, request: Request, *args: object, **kwargs: object
        ) -> Response:
            query_values = _retrieve_keys(request.query_params, query_params, "query")
            data_values = _retrieve_keys(request.data, data_params, "data")
            return function(
                self, request, *args, **kwargs, **query_values, **data_values
            )

        return wrapper

    return decorator


class BlossomUserMixin:
    REQUEST_FIELDS = {"v_id": "id", "v_username": "username", "username": "username"}

    def get_user_from_request(self, data: Dict) -> BlossomUser:
        """
        Retrieve the BlossomUser based on information provided within the request data.

        The user can be retrieved by its ID and / or its username using a combination of
        any of the following keys:
            - username:   The username
            - v_id:       The user ID
            - v_username: The username

        Note that when multiple values are present within the request, the user with
        the combination of these values is found.

        When either none of the above keys is provided or no user with the provided
        combination is found, an exception is raised.

        :param data: the dictionary from which data is used to retrieve the user
        :return: the requested user
        :raise ValidationError: when none of the descibed keys are present within the data
        :raise Http404: when the user with the described keys cannot be found
        """
        if not any(key in data for key in self.REQUEST_FIELDS.keys()):
            raise serializers.ValidationError(
                f"No key in {self.REQUEST_FIELDS.keys()} present."
            )

        # Get the BlossomUser corresponding to the fields present in the request data
        # and the mapping in the REQUEST_FIELDS constant.
        return get_object_or_404(
            BlossomUser,
            **{
                self.REQUEST_FIELDS[key]: value
                for key, value in data.items()
                if key in self.REQUEST_FIELDS.keys()
            },
        )
