import logging
import re
from typing import Dict, Union
from urllib.parse import urlparse

import requests
from django.conf import settings
from requests.exceptions import ConnectTimeout, RequestException
from requests.models import Response as RequestsResponse

from blossom.ocr.errors import OCRError

URL_RE = (
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]" r"|[*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
)
SPECIAL_CHARS = ["(", ")", "!", ".", ","]


def process_image(image_url: str) -> Union[None, Dict]:
    """Process an image with OCR using ocr.space."""

    def _set_error_state(response: Dict) -> Dict:
        """
        Build an error dictionary for a bad response.

        The information that's given in the full response is more than we need,
        so build a "lite" version and use that to present an error message.
        """
        error = {
            "exit_code": response["OCRExitCode"],
            "error_message": json_result.get("ErrorMessage"),
            "error_details": json_result.get("ErrorDetails"),
        }
        return error

    json_result = decode_image_from_url(image_url)

    if json_result.get("ParsedResults") is None:
        raise OCRError(_set_error_state(json_result))

    try:
        result = {
            "text": json_result["ParsedResults"][0]["ParsedText"],
            "exit_code": int(json_result["OCRExitCode"]),
            # this will change depending on how many pages we send it
            "page_exit_code": int(json_result["ParsedResults"][0]["FileParseExitCode"]),
            "error_on_processing": json_result["IsErroredOnProcessing"],
            # the API has stopped returning these two fields. The documentation
            # says that it should still be there, but they're only there on
            # an actual error now. We'll still keep looking for the fields, but
            # we won't make them required. First seen on 8/13/18
            "error_message": json_result.get("ErrorMessage", ""),
            "error_details": json_result.get("ErrorDetails", ""),
            # ignores errors per file, we should only get one file ever anyway.
            "process_time_in_ms": int(json_result["ProcessingTimeInMilliseconds"]),
        }
    except (KeyError, IndexError):
        raise OCRError(_set_error_state(json_result))

    # If there's no text, we might get back "", but just in case it's just
    # whitespace, we don't want it.
    if result["text"].strip() == "":
        return None

    if result["exit_code"] != 1 or result["error_on_processing"] or not result["text"]:
        raise OCRError(_set_error_state(json_result))

    else:
        return result


def _get_results_from_ocrspace(payload: Dict) -> RequestsResponse:
    """Major API logic from decode_image_from_url."""
    result = None
    for API in settings.OCR_API_URLS:  # noqa: N806
        try:
            # The timeout for this request goes until the first bit response,
            # not for the entire request process. If we don't hear anything
            # from the remote server for 10 seconds, throw a ConnectTimeout
            # and move on to the next one.
            result = requests.post(API, data=payload, timeout=10)
            # crash and burn if the API is down, or similar
            result.raise_for_status()

            if result.json()["OCRExitCode"] == 6:
                # process timed out waiting for response
                raise ConnectionError

            # if the request succeeds, we'll have a result. Therefore, just
            # break the loop here.
            break
        except (ConnectTimeout, ConnectionError):
            # Sometimes the ocr.space API will just... not respond. Move on.
            # Try the next API in the list, then release from the loop if we
            # exhaust our options.
            continue
        except RequestException as e:
            # we have a result object here but it's not right.
            if result is None:
                logging.warning(
                    f"Received null object because of a request exception. "
                    f"Attempted API: {API} | Error: {e}"
                )
            else:
                logging.error(
                    f"ERROR {result.status_code} with OCR:\n\nHEADERS:\n "
                    f"{repr(result.headers)}\n\nBODY:\n{repr(result.text)} "
                )
            continue
        except Exception as e:
            logging.error(f"Unknown error! Attempted API: {API} | Error: {e}")

    if result is None or not result.ok:
        raise ConnectionError("Attempted all three OCR.space APIs -- cannot connect!")

    return result


def decode_image_from_url(
    url: str, overlay: bool = False, api_key: str = settings.OCR_API_KEY
) -> Dict:
    """
    OCR.space API request with remote file.

    This code was originally borrowed from
    https://github.com/Zaargh/ocr.space_code_example/blob/master/ocrspace_example.py
    :param url: Image url.
    :param overlay: Is OCR.space overlay required in your response.
        Defaults to False.
    :param api_key: OCR.space API key.
        Defaults to environment variable "OCR_API_KEY"
        If it doesn't exist, it will use "helloworld"
    :return: Result in JSON format.
    """
    payload = {
        "url": url,
        "isOverlayRequired": overlay,
        "apikey": api_key,
    }

    result = _get_results_from_ocrspace(payload)

    # it is technically possible to reach this point with an object and a bad
    # json response. Let's check for that here.
    # noinspection PyBroadException
    try:
        return result.json()
    except:  # noqa: E722
        return {
            "OCRExitCode": 999,
            "ErrorMessage": "This request absolutely did not work as expected.",
            "error_details": "No json available for this response.",
        }


def escape_reddit_links(body: str) -> str:
    r"""
    Escape u/ and r/ links in a message.

    There is no (known) way to escape u/ or r/ (without a preceding slash),
    so those will also be changed to \/u/ and \/r/.  # noqa: W605
    :param body: the text to escape
    :return: the escaped text
    """
    body = body.replace("\r\n", "\n\n").replace(">>", r"\>\>")
    magic = re.compile(r"(?<![a-zA-Z0-9])([ur])/|/([ur])/")
    return magic.sub(r"\/\1\2/", body)


def _is_shortlink(url: str) -> bool:
    """Rule-based checker to identify short links."""
    # Long URLs aren't short.
    if len(url) > 30:
        return False

    url = urlparse(url)

    # if it's a bare hostname, it's not a shortlink
    if len(url.path) == 0 or url.path == "/":
        return False

    if len(url.path.split("/")) > 3:
        return False

    # what's after the hostname?
    if len(url.path) > 12:
        return False

    # how long is the host? http://asdfasdfasdfasdf.com isn't short.
    if len(url.netloc[: url.netloc.index(".")]) > 10:
        return False

    # Is it a complicated URL? https://a.com/b/c/d/?
    if len(url.path.split("/")) == 3:
        # check the difference between a.com/b/c and a.com/b/
        # black fights flake8 on formatting here, so black wins
        return len(url.path[url.path.rfind("/") :]) <= 1  # noqa: E203

    return True


def replace_shortlinks(content: str, replacement: str = "<redacted link>") -> str:
    """
    Pull out anything that looks like a shortlink and replace with a redacted string.

    So that we don't actually have to deal with _following_ the link, we adapt
    this answer from SO (https://stackoverflow.com/a/9557685) so that it it _looks_
    like a shortlink, just replace it to be on the safe side.
    """
    # pull out all the matches with finditer because findall doesn't preserve the
    # location of the matches
    matches = list(re.finditer(URL_RE, content))
    if len(matches) == 0:
        return content

    # go backwards so that we can replace multiple links without messing up the
    # location positions from changing the length of the strings
    for match in list(reversed(matches)):
        if _is_shortlink(match.group().strip("".join(SPECIAL_CHARS))):
            start, end = match.span()
            # if the last character is something that's not something we want,
            # leave it in place
            if match.group()[-1] in SPECIAL_CHARS:
                end -= 1
            content = content[:start] + replacement + content[end:]

    return content
