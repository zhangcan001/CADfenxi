from recognizer.common.result_types import OcrResult
from recognizer.ocr_engine.base import OcrEngine


class PaddleOcrEngine(OcrEngine):
    engine_name = "paddleocr"
    engine_version = "not_configured"

    def recognize(self, image_path: str) -> OcrResult:
        raise RuntimeError("PaddleOCR is not configured in v0.1 local tests")
