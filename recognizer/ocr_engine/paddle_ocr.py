"""PaddleOCR 引擎适配。

PaddleOCR 是可选依赖（不在 requirements.txt 里，便携包不内置）。
用户本地安装 paddleocr + paddlepaddle 后，本引擎自动可用；否则 ocr_service 会回退到
MockOcrEngine。延迟导入避免模块装载时报错。

兼容 PaddleOCR 2.x（旧 `.ocr()` 返回 `[[bbox, (text, score)], ...]`）与 3.x
（新 `.predict()` 返回带 `rec_texts/rec_scores/rec_polys` 的字典）。
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from recognizer.common.result_types import OcrItem, OcrResult
from recognizer.ocr_engine.base import OcrEngine

logger = logging.getLogger(__name__)


def is_paddleocr_available() -> bool:
    try:
        import paddleocr  # noqa: F401
        return True
    except ImportError:
        return False


class PaddleOcrEngine(OcrEngine):
    engine_name = "paddleocr"

    def __init__(self, lang: str = "ch") -> None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError("PaddleOCR not installed; install paddleocr to enable") from exc

        try:
            import paddleocr as _paddleocr_pkg
            self.engine_version = getattr(_paddleocr_pkg, "__version__", "unknown")
        except (ImportError, AttributeError):
            self.engine_version = "unknown"

        paddlex_home = os.environ.get("PADDLEX_HOME")
        default_home = Path.home() / ".paddlex"
        logger.info(
            "Initializing PaddleOCR: lang=%s, version=%s, PADDLEX_HOME=%r, ~/.paddlex exists=%s",
            lang,
            self.engine_version,
            paddlex_home,
            default_home.exists(),
        )
        t0 = time.monotonic()

        # 3.x API 用 use_textline_orientation；2.x 用 use_angle_cls + show_log。优先 3.x。
        # PaddlePaddle 3.3.x 的 mkldnn 后端 + PIR 运行时不兼容，强制关掉避免运行时报错。
        try:
            self._ocr = PaddleOCR(lang=lang, use_textline_orientation=True, enable_mkldnn=False)
            self._api = "v3"
        except (TypeError, ValueError):
            try:
                self._ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
                self._api = "v2"
            except Exception as exc:  # 初始化失败统一抛 RuntimeError 让上层回退
                raise RuntimeError(f"PaddleOCR init failed: {exc}") from exc

        logger.info("PaddleOCR ready in %.1fs (api=%s)", time.monotonic() - t0, self._api)

    def recognize(self, image_path: str) -> OcrResult:
        if self._api == "v3":
            return self._recognize_v3(image_path)
        return self._recognize_v2(image_path)

    def _recognize_v3(self, image_path: str) -> OcrResult:
        items: list[OcrItem] = []
        texts: list[str] = []
        try:
            results = self._ocr.predict(input=image_path)
        except Exception as exc:
            logger.exception("PaddleOCR v3 failed for %s", image_path)
            raise RuntimeError(f"PaddleOCR failed: {exc}") from exc

        for res in results or []:
            # res 是 dict-like：{'rec_texts': [...], 'rec_scores': [...], 'rec_polys': [...]}
            rec_texts = _safe_get(res, "rec_texts", [])
            rec_scores = _safe_get(res, "rec_scores", [])
            rec_polys = _safe_get(res, "rec_polys", [])
            for idx, text in enumerate(rec_texts or []):
                clean_text = (text or "").strip()
                if not clean_text:
                    continue
                score = rec_scores[idx] if idx < len(rec_scores) else 0.0
                poly = rec_polys[idx] if idx < len(rec_polys) else None
                texts.append(clean_text)
                items.append(
                    OcrItem(
                        text=clean_text,
                        confidence=float(score or 0.0),
                        bbox=_flatten_bbox(poly),
                    )
                )

        return OcrResult(
            text="\n".join(texts),
            items=items,
            engine_name=self.engine_name,
            engine_version=self.engine_version,
        )

    def _recognize_v2(self, image_path: str) -> OcrResult:
        items: list[OcrItem] = []
        texts: list[str] = []
        try:
            raw = self._ocr.ocr(image_path, cls=True)
        except Exception as exc:
            logger.exception("PaddleOCR v2 failed for %s", image_path)
            raise RuntimeError(f"PaddleOCR failed: {exc}") from exc

        for page in raw or []:
            if not page:
                continue
            for entry in page:
                try:
                    bbox_pts, (text, score) = entry
                except (TypeError, ValueError):
                    continue
                clean_text = (text or "").strip()
                if not clean_text:
                    continue
                texts.append(clean_text)
                items.append(
                    OcrItem(
                        text=clean_text,
                        confidence=float(score or 0.0),
                        bbox=_flatten_bbox(bbox_pts),
                    )
                )

        return OcrResult(
            text="\n".join(texts),
            items=items,
            engine_name=self.engine_name,
            engine_version=self.engine_version,
        )


def _safe_get(obj, key, default):
    try:
        if hasattr(obj, "get"):
            value = obj.get(key, default)
        else:
            value = getattr(obj, key, default)
    except (KeyError, AttributeError):
        return default
    if value is None:
        return default
    return value


def _flatten_bbox(points) -> list[int]:
    """转成 [xmin, ymin, xmax, ymax]。兼容 numpy 数组与 Python list。"""
    if points is None:
        return [0, 0, 0, 0]
    try:
        # 3.x rec_polys 是 numpy ndarray of shape (4, 2)
        pts = points.tolist() if hasattr(points, "tolist") else list(points)
        xs = [int(p[0]) for p in pts]
        ys = [int(p[1]) for p in pts]
        return [min(xs), min(ys), max(xs), max(ys)]
    except (TypeError, ValueError, IndexError):
        return [0, 0, 0, 0]
