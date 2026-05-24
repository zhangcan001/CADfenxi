"""OCR 引擎选择器。

优先选 PaddleOCR（若已安装且未禁用），否则回退 MockOcrEngine。
可通过环境变量 CADFENXI_DISABLE_PADDLEOCR=1 强制走 mock。
"""
from __future__ import annotations

import logging
import os

from recognizer.ocr_engine.base import OcrEngine
from recognizer.ocr_engine.mock_ocr import MockOcrEngine
from recognizer.ocr_engine.paddle_ocr import is_paddleocr_available

logger = logging.getLogger(__name__)

_cached_engine: OcrEngine | None = None
_cached_engine_failed: bool = False


def get_ocr_engine() -> OcrEngine:
    """返回当前可用的 OCR 引擎。结果被缓存（PaddleOCR 初始化较慢）。"""
    global _cached_engine, _cached_engine_failed

    if _cached_engine is not None:
        return _cached_engine

    disabled = os.getenv("CADFENXI_DISABLE_PADDLEOCR", "").strip().lower() in {"1", "true", "yes"}
    paddle_available = is_paddleocr_available()
    logger.info(
        "OCR engine resolve: disabled=%s, paddle_available=%s, previously_failed=%s",
        disabled,
        paddle_available,
        _cached_engine_failed,
    )
    if not disabled and not _cached_engine_failed and paddle_available:
        try:
            from recognizer.ocr_engine.paddle_ocr import PaddleOcrEngine
            _cached_engine = PaddleOcrEngine()
            logger.info("OCR engine: PaddleOCR initialized (version=%s)", _cached_engine.engine_version)
            return _cached_engine
        except (RuntimeError, ImportError, OSError) as exc:
            logger.warning("PaddleOCR init failed (%s); falling back to MockOcrEngine", exc)
            _cached_engine_failed = True

    logger.info("OCR engine: MockOcrEngine (will return empty text)")
    _cached_engine = MockOcrEngine()
    return _cached_engine


def reset_cache() -> None:
    """测试用：清掉引擎缓存。"""
    global _cached_engine, _cached_engine_failed
    _cached_engine = None
    _cached_engine_failed = False
