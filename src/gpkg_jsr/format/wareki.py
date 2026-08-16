"""和暦 (元号) 変換 (SP-04-01, SP-04-02, SP-04-04)。

明治以前 (江戸期の各元号および明治への改元) の境界は年単位の精度でのみ扱う。
日本が太陽暦を採用したのは明治 6 年 (1873) であり、それ以前の改元日を
グレゴリオ暦の日付として正確に特定する手段がないため（[ADR-03] と同じ理由で、
検証できない日単位の精度を実装に持ち込まない）。大正以降の改元は歴史的に確定した
グレゴリオ暦日であり、日単位の精度で扱う。

[ADR-03]: ../../../docs/20_architecture.md
"""
from __future__ import annotations

from dataclasses import dataclass

from .kanji_number import kanji_number

# (year, month, day) の 3 要素タプル。明治以前の境界は month=1, day=1 に固定する
# (年単位の精度の表明。上記モジュール docstring 参照)。
_DateTriple = tuple[int, int, int]

# 太陽暦 (グレゴリオ暦) 採用日。これより前の日付は月日を確定表示しない (SP-04-04)。
GREGORIAN_ADOPTION_DATE: _DateTriple = (1873, 1, 1)


@dataclass(frozen=True)
class Era:
    name: str
    start: _DateTriple
    end: _DateTriple | None  # None は現行の元号 (無期限)


ERAS: tuple[Era, ...] = (
    Era("慶長", (1596, 1, 1), (1615, 1, 1)),
    Era("元和", (1615, 1, 1), (1624, 1, 1)),
    Era("寛永", (1624, 1, 1), (1644, 1, 1)),
    Era("正保", (1644, 1, 1), (1648, 1, 1)),
    Era("慶安", (1648, 1, 1), (1652, 1, 1)),
    Era("承応", (1652, 1, 1), (1655, 1, 1)),
    Era("明暦", (1655, 1, 1), (1658, 1, 1)),
    Era("万治", (1658, 1, 1), (1661, 1, 1)),
    Era("寛文", (1661, 1, 1), (1673, 1, 1)),
    Era("延宝", (1673, 1, 1), (1681, 1, 1)),
    Era("天和", (1681, 1, 1), (1684, 1, 1)),
    Era("貞享", (1684, 1, 1), (1688, 1, 1)),
    Era("元禄", (1688, 1, 1), (1704, 1, 1)),
    Era("宝永", (1704, 1, 1), (1711, 1, 1)),
    Era("正徳", (1711, 1, 1), (1716, 1, 1)),
    Era("享保", (1716, 1, 1), (1736, 1, 1)),
    Era("元文", (1736, 1, 1), (1741, 1, 1)),
    Era("寛保", (1741, 1, 1), (1744, 1, 1)),
    Era("延享", (1744, 1, 1), (1748, 1, 1)),
    Era("寛延", (1748, 1, 1), (1751, 1, 1)),
    Era("宝暦", (1751, 1, 1), (1764, 1, 1)),
    Era("明和", (1764, 1, 1), (1772, 1, 1)),
    Era("安永", (1772, 1, 1), (1781, 1, 1)),
    Era("天明", (1781, 1, 1), (1789, 1, 1)),
    Era("寛政", (1789, 1, 1), (1801, 1, 1)),
    Era("享和", (1801, 1, 1), (1804, 1, 1)),
    Era("文化", (1804, 1, 1), (1818, 1, 1)),
    Era("文政", (1818, 1, 1), (1830, 1, 1)),
    Era("天保", (1830, 1, 1), (1844, 1, 1)),
    Era("弘化", (1844, 1, 1), (1848, 1, 1)),
    Era("嘉永", (1848, 1, 1), (1854, 1, 1)),
    Era("安政", (1854, 1, 1), (1860, 1, 1)),
    Era("万延", (1860, 1, 1), (1861, 1, 1)),
    Era("文久", (1861, 1, 1), (1864, 1, 1)),
    Era("元治", (1864, 1, 1), (1865, 1, 1)),
    Era("慶応", (1865, 1, 1), (1868, 1, 1)),
    Era("明治", (1868, 1, 1), (1912, 7, 30)),
    Era("大正", (1912, 7, 30), (1926, 12, 25)),
    Era("昭和", (1926, 12, 25), (1989, 1, 8)),
    Era("平成", (1989, 1, 8), (2019, 5, 1)),
    Era("令和", (2019, 5, 1), None),
)


@dataclass(frozen=True)
class WarekiYear:
    era_name: str
    era_year: int  # 1 = 元年


def wareki_candidates(
    year: int, month: int | None = None, day: int | None = None
) -> list[WarekiYear]:
    """year (+ 任意で month, day) に対応する元号年の候補を返す。

    通常は要素数 1。month/day が不明で、かつ対象の年が複数の元号にまたがりうる
    改元境界年 (大正以降のみ発生しうる。SP-04-02 参照) の場合に限り、要素数 2 の
    候補リストを返す。テーブル範囲外 (慶長元年 = 1596 年より前) の場合は空リストを返す。
    """
    if month is not None and day is not None:
        query = (year, month, day)
        for era in ERAS:
            if era.start <= query and (era.end is None or query < era.end):
                return [WarekiYear(era.name, _era_year(era, year))]
        return []

    # 年のみが既知の場合: その暦年に懸かる元号すべてを候補とする。
    matches = [era for era in ERAS if _year_overlaps_era(year, era)]
    return [WarekiYear(era.name, _era_year(era, year)) for era in matches]


def _year_overlaps_era(year: int, era: Era) -> bool:
    start_year = era.start[0]
    end_year = era.end[0] if era.end is not None else None
    if year < start_year:
        return False
    if end_year is None:
        return True
    if year > end_year:
        return False
    if year < end_year:
        return True
    # year == end_year: 改元境界年。終了日が 1/1 ちょうど (=年単位精度の元号) なら
    # その年はすでに次の元号に属し、この era には含まれない。
    return era.end != (end_year, 1, 1)


def _era_year(era: Era, year: int) -> int:
    return year - era.start[0] + 1


def format_wareki_year(year: int, month: int | None = None, day: int | None = None) -> str:
    """年 (+ 任意で月日) を「明治二十七年」のような和暦の年表記に変換する。

    改元境界年で候補が複数ある場合は「明治四十五年/大正元年」のように併記する。
    テーブル範囲外の場合は ValueError を送出する。
    """
    candidates = wareki_candidates(year, month, day)
    if not candidates:
        raise ValueError(f"year {year} is out of the supported era table range")
    return "/".join(_format_single(c) for c in candidates)


def _format_single(candidate: WarekiYear) -> str:
    if candidate.era_year == 1:
        return f"{candidate.era_name}元年"
    return f"{candidate.era_name}{kanji_number(candidate.era_year)}年"


def is_pre_gregorian_adoption(year: int, month: int | None, day: int | None) -> bool:
    """太陽暦採用日 (1873-01-01) より前の日付かどうかを判定する (SP-04-04, ADR-03)。

    月日が不明な場合は年だけで判定する。年が 1873 ちょうどで月日が不明な場合は
    確実に「採用前」とは言い切れないため、安全側 (= 採用前ではない = 月日を
    隠さない) に倒す。
    """
    if year < GREGORIAN_ADOPTION_DATE[0]:
        return True
    if year > GREGORIAN_ADOPTION_DATE[0]:
        return False
    if month is None or day is None:
        return False
    return (year, month, day) < GREGORIAN_ADOPTION_DATE
