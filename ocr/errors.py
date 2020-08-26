from typing import Dict


class OCRError(Exception):
    # all codes from https://ocr.space/ocrapi
    OCR_EXIT_CODES = {
        1: "parsed successfully",
        2: "parsed partially",
        3: "ENGINE ERROR: all pages failed",
        4: "ENGINE ERROR: FATAL",
        6: "Timed out while waiting for results",
        99: "Not a valid URL; invalid image or pdf",
        # our error message for a request that is very, very broken
        999: "Something went horribly wrong",
    }

    PAGE_EXIT_CODES = {
        1: "success",
        0: "file not found",
        -10: "OCR engine parse error",
        -20: "timeout",
        -30: "validation error",
        -99: "UNKNOWN ERROR",
        3: "File failed validation",  # This is not documented, beware!
    }

    def __init__(self, result: Dict) -> None:  # noqa D107
        super(OCRError, self).__init__(
            self.PAGE_EXIT_CODES.get(
                result["exit_code"],
                f"Unrecognized error: Code {result['exit_code']}, "
                f"{result['error_message']}: {result['error_details']}",
            )
        )
        self.result = result
