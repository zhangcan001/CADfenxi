from abc import ABC, abstractmethod

from recognizer.common.result_types import OcrResult


class OcrEngine(ABC):
    engine_name: str
    engine_version: str

    @abstractmethod
    def recognize(self, image_path: str) -> OcrResult:
        raise NotImplementedError
