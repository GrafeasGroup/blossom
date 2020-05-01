from functools import wraps
from typing import Dict, Set

from rest_framework import serializers, status
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


def validate_request(query_params: Set = None, data_params: Set = None):
    """
    Validate arguments of the Request within inner method.

    This decorator is to be used ONLY around a method which has access to
    a Request object as its first positional argument, as this object is
    validated within the decorator.

    In the parameters query_params and data_params the user can provide a set
    of parameters which the request query and data should contain respectively.

    Note that as of now only the existence of a key within these two
    dictionaries is checked; no further validation is yet done.

    :param query_params: the set of query parameters which should exist in the Request.
    :param data_params: the set of data parameters which should exist in the Request.
    :return: the decorator which wraps this function.
    """
    query_params = set() if query_params is None else query_params
    data_params = set() if data_params is None else data_params

    def decorator(function):
        @wraps(function)
        def wrapper(
            self: object, request: Request, *args: object, **kwargs: object
        ) -> Response:
            query_values = _retrieve_keys(request.query_params, query_params, "query")
            data_values = _retrieve_keys(request.data, data_params, "data")
            combined = {**query_values, **data_values}
            combined.update(
                {
                    key: (query_values[key], data_values[key])
                    for key in query_values
                    if key in data_values
                }
            )
            return function(self, request, *args, **kwargs, **combined)

        return wrapper

    return decorator


class BlossomUserMixin:
    REQUEST_FIELDS = {"v_id": "id", "v_username": "username", "username": "username"}

    def get_user_from_request(self, data: Dict) -> [BlossomUser, Response]:
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
        combination is found, a Response with a 400 and 404 status is returned
        respectively.

        :param data: the dictionary from which data is used to retrieve the user
        :return: the requested user or an error Response based on errors
        """
        if not any(key in data for key in self.REQUEST_FIELDS.keys()):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Filter the BlossomUsers on fields present in the request data according to the
        # mapping in the REQUEST_FIELDS constant.
        user = BlossomUser.objects.filter(
            **{
                self.REQUEST_FIELDS[key]: value
                for key, value in data.items()
                if key in self.REQUEST_FIELDS.keys()
            }
        ).first()
        return user if user else Response(status=status.HTTP_404_NOT_FOUND)
