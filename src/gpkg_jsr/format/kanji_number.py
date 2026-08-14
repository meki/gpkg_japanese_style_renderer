"""位取りなし漢数字への変換 (SP-04-03)。

年・月・日のような小さな整数を「二十七」「千八百六十八」のような、位取り記法
(一, 十, 百, 千) を用いた漢数字表記に変換する。「元年」等の暦特有の表記規則は
含まない (呼び出し側、主に format/wareki.py の責務)。
"""
from __future__ import annotations

_DIGITS = ("", "一", "二", "三", "四", "五", "六", "七", "八", "九")
_UNITS = ("", "十", "百", "千")


def kanji_number(value: int) -> str:
    """0 <= value <= 9999 の整数を漢数字表記の文字列に変換する。

    位取り (十/百/千) の先頭が 1 のとき「一」を省略する（例: 11 -> 十一,
    100 -> 百, 101 -> 百一）標準的な表記規則に従う。
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"value must be an int, got {type(value).__name__}")
    if not 0 <= value <= 9999:
        raise ValueError(f"value must be in [0, 9999], got {value}")

    if value == 0:
        return "〇"

    digits = [int(c) for c in str(value)]
    length = len(digits)
    parts: list[str] = []
    for index, digit in enumerate(digits):
        place = length - index - 1
        if digit == 0:
            continue
        if place == 0:
            parts.append(_DIGITS[digit])
        elif digit == 1:
            parts.append(_UNITS[place])
        else:
            parts.append(_DIGITS[digit] + _UNITS[place])
    return "".join(parts)
