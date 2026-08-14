"""家系姓の判定・婚入配偶者の姓省略・旧姓の取り込み (SP-01-05, SP-03-02, SP-03-03)。"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Set
from typing import cast

from gpkg_jsr.gramps.gpkg_reader import Person

DEFAULT_LINEAGE_MIN_RATIO = 0.5


def infer_lineage_surnames(
    people: Iterable[Person], min_ratio: float = DEFAULT_LINEAGE_MIN_RATIO
) -> frozenset[str]:
    """姓の出現頻度から家系姓を推定する (SP-03-02)。

    最頻出の姓の出現回数に対し `min_ratio` 以上の頻度を持つ姓をすべて家系姓と
    みなす（複数の家系を統合した家系図で家系姓が複数になるケースを想定）。
    空文字列の姓（姓不明・婚入配偶者に多い）は対象外とする。

    これはあくまで既定値の推定であり、利用者が上書きできることを前提とする
    (RQ-03-02)。
    """
    counts = Counter(p.primary_name.surname for p in people if p.primary_name.surname)
    if not counts:
        return frozenset()
    threshold = max(counts.values()) * min_ratio
    return frozenset(surname for surname, count in counts.items() if count >= threshold)


def is_spouse_in(person: Person, lineage_surnames: Set[str]) -> bool:
    """人物が婚入配偶者（家系姓を持たない）かどうかを判定する (SP-03-02)。"""
    return person.primary_name.surname not in lineage_surnames


def former_surname(person: Person) -> str | None:
    """`<name type="Also Known As" alt="1">` から旧姓を取り出す (SP-01-05, SP-03-03)。

    複数存在する場合は最初の 1 件を採用する。存在しなければ None。
    """
    for name in person.names:
        if name.is_alt and name.type == "Also Known As" and name.surname:
            # person.names は移設元 gpkg_reader.py の list[Any] フィールドのため、
            # ここで明示的に str であることを表明する。
            return cast(str, name.surname)
    return None
