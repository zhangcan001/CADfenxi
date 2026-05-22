from recognizer.common.result_types import OcrResult
from recognizer.ocr_engine.base import OcrEngine


class MockOcrEngine(OcrEngine):
    engine_name = "mock_ocr"
    engine_version = "0.1.0"

    def recognize(self, image_path: str) -> OcrResult:
        return OcrResult(
            text="",
            items=[],
            engine_name=self.engine_name,
            engine_version=self.engine_version,
        )
