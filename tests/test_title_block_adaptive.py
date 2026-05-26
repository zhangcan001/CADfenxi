"""标题栏自适应定位测试。"""
from __future__ import annotations

from recognizer.cad_engine.title_area import (
    find_title_block_bbox,
    find_title_block_bbox_adaptive,
)


def _text(x: float, y: float, value: str = "x") -> dict:
    return {
        "clean_text": value,
        "insert": [x, y, 0],
        "height": 2.5,
        "layer": "0",
    }


def _insert(name: str, x: float = 0.0, y: float = 0.0) -> dict:
    return {
        "block_name": name,
        "layer": "0",
        "insert": [x, y, 0.0],
    }


def test_finds_title_when_insert_present():
    inserts = [_insert("TITLEBLOCK", 1000.0, 50.0)]
    texts = [_text(0, 0)]
    bbox = find_title_block_bbox_adaptive(inserts, texts)
    assert bbox is not None
    # 优先使用 INSERT 命中路径（半径 ±400/±250）
    expected = find_title_block_bbox(inserts)
    assert bbox == expected


def test_falls_back_to_text_density_when_no_insert():
    # 大量文字均匀分散
    sparse = [_text(x, y) for x in range(0, 500, 100) for y in range(0, 500, 100)]
    # 在右下象限堆一个明显的文字密集簇
    cluster = []
    for col in range(6):
        for row in range(3):
            cluster.append(_text(400 + col * 5, 50 + row * 5))
    texts = sparse + cluster
    bbox = find_title_block_bbox_adaptive([], texts)
    assert bbox is not None
    xmin, ymin, xmax, ymax = bbox
    # 命中区域应大致落在右下簇里
    assert xmin <= 400 <= xmax
    assert ymin <= 60 <= ymax


def test_returns_none_when_no_clear_density_cluster():
    # 仅 4 个文字，<8 阈值
    texts = [_text(x, y) for x in (10, 20) for y in (10, 20)]
    bbox = find_title_block_bbox_adaptive([], texts)
    assert bbox is None
