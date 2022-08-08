from copy import deepcopy
from typing import Dict
from unittest.mock import patch

from pytest import raises
from requests.exceptions import RequestException

from blossom.ocr.errors import OCRError
from blossom.ocr.helpers import decode_image_from_url, process_image

DEFAULT_OCRSPACE_RESPONSE = {
    "ParsedResults": [{"ParsedText": "AAA", "FileParseExitCode": 1}],
    "OCRExitCode": 1,
    "IsErroredOnProcessing": False,
    "ProcessingTimeInMilliseconds": 20,
}

# these fields are only returned on an error response
OCRSPACE_ERROR_FIELDS = {"ErrorMessage": "BBB", "ErrorDetails": "CCC"}


class TestProcessImage:
    def test_normal(self) -> None:
        """Verify that it works under normal conditions."""
        with patch(
            "blossom.ocr.helpers.decode_image_from_url",
            return_value=DEFAULT_OCRSPACE_RESPONSE,
        ):
            result = process_image("A")

        assert result["text"] == "AAA"
        assert result["exit_code"] == 1
        assert result["page_exit_code"] == 1
        assert result["error_on_processing"] is False
        assert result["error_message"] == ""
        assert result["error_details"] == ""
        assert result["process_time_in_ms"] == 20

    def test_ocrexception(self) -> None:
        """Verify that OCRExitCodes are parsed appropriately."""
        ocrspace_response = deepcopy(DEFAULT_OCRSPACE_RESPONSE)
        ocrspace_response.update(OCRSPACE_ERROR_FIELDS)
        ocrspace_response["OCRExitCode"] = 4  # fatal error
        del ocrspace_response["ParsedResults"]

        with patch(
            "blossom.ocr.helpers.decode_image_from_url", return_value=ocrspace_response
        ):
            with raises(OCRError):
                process_image("A")

    def test_malformed_response(self) -> None:
        """Verify that a dictionary missing required keys triggers an OCRError."""
        ocrspace_response = deepcopy(DEFAULT_OCRSPACE_RESPONSE)
        del ocrspace_response["IsErroredOnProcessing"]

        with patch(
            "blossom.ocr.helpers.decode_image_from_url", return_value=ocrspace_response
        ):
            with raises(OCRError):
                process_image("A")

    def test_empty_text_response(self) -> None:
        """Verify that an image with no text is returned as None."""
        ocrspace_response = deepcopy(DEFAULT_OCRSPACE_RESPONSE)
        ocrspace_response["ParsedResults"][0]["ParsedText"] = ""
        with patch(
            "blossom.ocr.helpers.decode_image_from_url", return_value=ocrspace_response
        ):
            result = process_image("A")

        assert result is None

    def test_failed_ocr(self) -> None:
        """Verify that an errored file from ocr.space results in an OCRError."""
        ocrspace_response = deepcopy(DEFAULT_OCRSPACE_RESPONSE)
        ocrspace_response.update(OCRSPACE_ERROR_FIELDS)
        ocrspace_response["IsErroredOnProcessing"] = True

        with patch(
            "blossom.ocr.helpers.decode_image_from_url", return_value=ocrspace_response
        ):
            with raises(OCRError):
                process_image("A")


class TestDecodeImage:
    def test_valid_response(self) -> None:
        """Verify that a proper response is processed appropriately."""

        class ValidTestResponse:
            ok = True

            def json(self) -> Dict:
                """Stub for requests."""
                return DEFAULT_OCRSPACE_RESPONSE

            def raise_for_status(self) -> None:
                """Stub for requests."""
                return None

        with patch("requests.post", return_value=ValidTestResponse()):
            result = decode_image_from_url("AAA")
        assert result == DEFAULT_OCRSPACE_RESPONSE

    def test_error_response(self) -> None:
        """Verify that generic failures trigger the API fallthrough process."""

        class FailTestResponse:
            ok = False

            def raise_for_status(self) -> bool:
                """Stub for requests."""
                return True

            def json(self) -> Dict:
                """Stub for requests."""
                resp = deepcopy(DEFAULT_OCRSPACE_RESPONSE)
                resp.update(OCRSPACE_ERROR_FIELDS)
                return resp

        with patch("requests.post", return_value=FailTestResponse()):
            with raises(ConnectionError) as e:
                decode_image_from_url("AAA")

            assert (
                e.value.args[0]
                == "Attempted all three OCR.space APIs -- cannot connect!"
            )

    def test_ocr_timeout(self) -> None:
        """# noqa: D205,D210,D400
        Verify that a ConnectionError is triggered if the API responds but returns an
        internal timeout.

        Black and flake8 disagree on how this should be formatted. Black wins.
        """

        class OCRTimeoutResponse:
            ok = False

            def raise_for_status(self) -> None:
                """Stub for requests."""
                return False

            def json(self) -> Dict:
                """Stub for requests."""
                resp = deepcopy(DEFAULT_OCRSPACE_RESPONSE)
                resp.update(OCRSPACE_ERROR_FIELDS)
                resp["OCRExitCode"] = 6
                return resp

        with patch("requests.post", return_value=OCRTimeoutResponse()):
            with raises(ConnectionError):
                decode_image_from_url("AAA")

    def test_malformed_response(self) -> None:
        """Verify that a malformed response triggers the manual error status."""

        class OCRUnknownResponse:
            ok = True
            status_code = 999
            headers = "ASDF"
            text = "QWER"

            def raise_for_status(self) -> bool:
                """Stub for requests."""
                return False

            def json(self) -> None:
                """Stub for requests."""
                raise Exception

        with patch("requests.post", return_value=OCRUnknownResponse()):
            result = decode_image_from_url("AAA")

        assert len(result) == 3
        assert result["OCRExitCode"] == 999

    def test_malformed_response_alt(self) -> None:
        """Verify that a malformed request is handled appropriately."""

        class OCRUnknownResponse:
            ok = True
            status_code = 999
            headers = "ASDF"
            text = "QWER"

            def raise_for_status(self) -> None:
                """Stub for requests."""
                raise RequestException

            def json(self) -> None:
                """Stub for requests."""
                raise Exception

        with patch("requests.post", return_value=OCRUnknownResponse()):
            result = decode_image_from_url("AAA")

        assert len(result) == 3
        assert result["OCRExitCode"] == 999

    def test_unknown_ocr_error_no_result(self) -> None:
        """# noqa: D200,D205,D210,D400
        Verify that if no result is obtained from the API, a ConnectionError is raised.
        """
        with patch("requests.post", side_effect=RequestException()):
            with raises(ConnectionError):
                decode_image_from_url("AAA")
