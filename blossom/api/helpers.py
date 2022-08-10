import threading
from functools import wraps
from typing import Any, Callable, Dict, Set, Tuple, Union

import pytz
from django.utils import timezone
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response


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


def get_time_since_open(
    days: bool = False,
) -> Tuple[Union[int, float], Union[int, float]]:
    """
    Return the number of days since the day we opened.

    Returns a tuple of (years, remainder days in year). For example, (3, 103)
    would be three years, 103 days.
    """
    # the autoformatter thinks this is evil if it's all on one line.
    # Breaking it up a little for my own sanity.
    start_date = pytz.timezone("UTC").localize(
        timezone.datetime(day=1, month=4, year=2017), is_dst=None
    )
    if days:
        return (timezone.now() - start_date).days
    else:
        return divmod((timezone.now() - start_date).days, 365)


def fire_and_forget(
    func: Callable[[Any], Any], *args: Tuple, **kwargs: Dict
) -> Callable[[Any], Any]:
    """
    Decorate functions to build a thread for a given function and trigger it.

    Originally from https://stackoverflow.com/a/59043636, this function
    prepares a thread for a given function and then starts it, intentionally
    severing communication with the thread so that we can continue moving
    on.

    This should be used sparingly and only when we are 100% sure that
    the function we are passing does not need to communicate with the main
    process and that it will exit cleanly (and that if it explodes, we don't
    care).
    """

    def wrapped(*args: Tuple, **kwargs: Dict) -> None:
        threading.Thread(target=func, args=(args), kwargs=kwargs).start()

    return wrapped
