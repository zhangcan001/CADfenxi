from dataclasses import dataclass, field


@dataclass
class OcrItem:
    text: str
    confidence: float
    bbox: list[int]


@dataclass
class OcrResult:
    text: str
    items: list[OcrItem] = field(default_factory=list)
    engine_name: str = "mock_ocr"
    engine_version: str = "0.1.0"
