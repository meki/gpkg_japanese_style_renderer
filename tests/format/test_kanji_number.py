from __future__ import annotations

import pytest

from gpkg_jsr.format.kanji_number import kanji_number


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "〇"),
        (1, "一"),
        (9, "九"),
        (10, "十"),
        (11, "十一"),
        (20, "二十"),
        (27, "二十七"),
        (45, "四十五"),
        (64, "六十四"),
        (99, "九十九"),
        (100, "百"),
        (101, "百一"),
        (110, "百十"),
        (999, "九百九十九"),
        (1000, "千"),
        (1868, "千八百六十八"),
        (9999, "九千九百九十九"),
    ],
)
def test_kanji_number(value: int, expected: str) -> None:
    assert kanji_number(value) == expected


@pytest.mark.parametrize("value", [-1, 10000])
def test_kanji_number_out_of_range(value: int) -> None:
    with pytest.raises(ValueError):
        kanji_number(value)


@pytest.mark.parametrize("value", ["5", 5.0, True])
def test_kanji_number_rejects_non_int(value: object) -> None:
    with pytest.raises(TypeError):
        kanji_number(value)  # type: ignore[arg-type]
