"""関係グラフの走査: 世代割当・到達可能集合計算 (SP-01-02, SP-02-01, SP-05-01)。

`Person.childof` / `parentin` は複数ありうる (養子縁組・再婚) ため、木ではなく
DAG として扱う。実データに閉路は存在しない前提 (GPKG_FORMAT_NOTES.md) だが、
万一データが壊れていて閉路を含む場合でも無限ループにならないよう、世代割当は
反復回数の上限を設けて安全側に倒す。
"""
from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from typing import Literal

from gpkg_jsr.gramps.gpkg_reader import GrampsDatabase, Person

Direction = Literal["ancestors", "descendants", "both"]

# 1 人あたりの世代再割当てが起こりうる最大回数の目安。DAG であれば十分な余裕を
# 持つ定数で、これを超えたら閉路混入など想定外のデータと判断して例外を送出する。
_MAX_RELAXATIONS_PER_PERSON = 10


def assign_generations(
    db: GrampsDatabase, roots: Iterable[Person] | None = None
) -> dict[str, int]:
    """起点人物集合からの幅優先探索で人物 handle ごとに世代番号を割り当てる (SP-02-01)。

    同一人物が複数経路で到達される場合は最小の世代番号を採用する。`roots` を
    省略した場合は `db.roots()` (childof を持たない人物) を起点とする。

    注意: `db.roots()` の大半は血統の祖先ではなく婚入配偶者であることが多い
    (実データでは 46 名のルートの大半がこれに該当)。婚入配偶者を起点集合に
    含めたまま図全体の世代を決めると、その配偶者の子が血統をたどった場合より
    浅い世代で先に到達され、最小世代優先の規則により複数世代が同じ世代番号に
    潰れうる (詳細は 10_specifications.md の SP-02-01 を参照)。レイアウト用途では
    `roots` に単一の血統起点、または婚入配偶者を除いた起点集合を明示的に渡すこと。
    """
    root_list = list(roots) if roots is not None else db.roots()
    generation: dict[str, int] = {}
    queue: deque[tuple[Person, int]] = deque((root, 0) for root in root_list)
    relaxations = 0
    max_relaxations = len(db.people) * _MAX_RELAXATIONS_PER_PERSON

    while queue:
        person, gen = queue.popleft()
        current = generation.get(person.handle)
        if current is not None and current <= gen:
            continue

        relaxations += 1
        if relaxations > max_relaxations:
            raise RuntimeError(
                "assign_generations: relaxation count exceeded the expected bound; "
                "the relationship graph may contain a cycle"
            )

        generation[person.handle] = gen
        for child in db.children(person):
            queue.append((child, gen + 1))

    return generation


def reachable_descendants(db: GrampsDatabase, root: Person) -> set[str]:
    """root から子孫方向へ辿れる人物 handle の集合 (root 自身を含む) を返す。"""
    visited = {root.handle}
    queue: deque[Person] = deque([root])
    while queue:
        person = queue.popleft()
        for child in db.children(person):
            if child.handle not in visited:
                visited.add(child.handle)
                queue.append(child)
    return visited


def reachable_ancestors(db: GrampsDatabase, root: Person) -> set[str]:
    """root から祖先方向へ辿れる人物 handle の集合 (root 自身を含む) を返す。"""
    visited = {root.handle}
    queue: deque[Person] = deque([root])
    while queue:
        person = queue.popleft()
        for father, mother, _frel, _mrel in db.parents(person):
            for parent in (father, mother):
                if parent is not None and parent.handle not in visited:
                    visited.add(parent.handle)
                    queue.append(parent)
    return visited


def reachable_people(db: GrampsDatabase, root: Person, direction: Direction) -> set[str]:
    """SP-05-01: 起点人物から指定方向へ到達可能な人物 handle の集合を返す。

    `direction` が `"both"` の場合は子孫方向・祖先方向の到達可能集合の和集合。
    """
    if direction == "descendants":
        return reachable_descendants(db, root)
    if direction == "ancestors":
        return reachable_ancestors(db, root)
    if direction == "both":
        return reachable_descendants(db, root) | reachable_ancestors(db, root)
    raise ValueError(f"unknown direction: {direction!r}")
