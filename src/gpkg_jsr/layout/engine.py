"""自動レイアウト計算 (SP-02, 粗い版。ノード重なり・エッジ交差の解消は Phase 6)。

処理の流れ:

1. `root` の血統子孫全員を `model.graph.assign_generations` の世代割当で対象人物
   とする。配偶者は各人物に隣接して配置するため、対象集合へ追加で取り込む。
2. 各人物の抽象寸法を `layout.metrics.estimate_node_size` で見積もる。
3. `db.children()` (生年昇順) を用いて部分木の占有幅をボトムアップで計算し
   (`_subtree_width`)、親を子の中央に揃える形でトップダウンに x 座標を確定する
   (`_assign_positions`)。配偶者は人物のすぐ隣に配置し、家系側の人物を先
   (＝抽象座標の x が小さい側) に置く。
4. 世代ごとの y 座標は、その世代で最も高いノードに合わせた行として確定する
   (上揃え)。
5. 両親が揃って対象集合に含まれる family から夫婦連結線 (MarriageEdge) を、
   family の子のうち対象集合に含まれる人物へ親子接続線 (ChildEdge) を生成する。
6. 配偶者の実親が判明していれば、その配偶者の直上に補助ノード (auxiliary_nodes)
   として追加する (SP-02-06)。補助ノードは幅計算・重なり回避の対象に含めない。

x 座標の昇順は「年長者から並べた出現順」(0 が最年長) であり、日本式の
右→左表示への変換は描画層の責務とする (layout/types.py の docstring 参照)。
"""
from __future__ import annotations

from collections.abc import Set
from dataclasses import dataclass, field

from gpkg_jsr.gramps.gpkg_reader import GrampsDatabase, Person
from gpkg_jsr.layout.metrics import estimate_node_size
from gpkg_jsr.layout.types import (
    ChildEdge,
    DisplayOptions,
    LayoutResult,
    MarriageEdge,
    NodeSize,
    PersonNode,
)
from gpkg_jsr.model.graph import assign_generations
from gpkg_jsr.model.view import Calendar, PersonView, build_person_view

SIBLING_GAP = 1.0
SPOUSE_GAP = 0.3
GENERATION_GAP = 2.0
AUXILIARY_OFFSET = 1.5


@dataclass
class _Context:
    db: GrampsDatabase
    sizes: dict[str, NodeSize]
    subtree_width: dict[str, float] = field(default_factory=dict)
    x_position: dict[str, float] = field(default_factory=dict)  # 各人物ノードの左端 x


def _couple_width(context: _Context, person: Person) -> float:
    width = context.sizes[person.handle].width
    for spouse in context.db.spouses(person):
        width += SPOUSE_GAP + context.sizes[spouse.handle].width
    return width


def _subtree_width(context: _Context, person: Person) -> float:
    if person.handle in context.subtree_width:
        return context.subtree_width[person.handle]

    couple_width = _couple_width(context, person)
    children = context.db.children(person)
    if not children:
        result = couple_width
    else:
        children_width = sum(_subtree_width(context, c) for c in children)
        children_width += SIBLING_GAP * (len(children) - 1)
        result = max(couple_width, children_width)

    context.subtree_width[person.handle] = result
    return result


def _assign_positions(context: _Context, person: Person, x_start: float) -> None:
    """[x_start, x_start + _subtree_width(person)) の区間に person とその子孫を配置する。"""
    width = context.subtree_width[person.handle]
    children = context.db.children(person)

    if children:
        children_width = sum(context.subtree_width[c.handle] for c in children)
        children_width += SIBLING_GAP * (len(children) - 1)
        cursor = x_start + max(0.0, (width - children_width) / 2)
        child_centers: list[float] = []
        for child in children:
            child_width = context.subtree_width[child.handle]
            _assign_positions(context, child, cursor)
            child_centers.append(cursor + child_width / 2)
            cursor += child_width + SIBLING_GAP
        couple_center = (child_centers[0] + child_centers[-1]) / 2
    else:
        couple_center = x_start + width / 2

    couple_width = _couple_width(context, person)
    x = couple_center - couple_width / 2
    context.x_position[person.handle] = x
    x += context.sizes[person.handle].width + SPOUSE_GAP
    for spouse in context.db.spouses(person):
        context.x_position[spouse.handle] = x
        x += context.sizes[spouse.handle].width + SPOUSE_GAP


def _center_x(context: _Context, handle: str) -> float:
    return context.x_position[handle] + context.sizes[handle].width / 2


def build_layout(
    db: GrampsDatabase,
    root: Person,
    *,
    calendar: Calendar = "wareki",
    display_options: DisplayOptions | None = None,
    focus_person_handle: str | None = None,
    lineage_surnames: Set[str] | None = None,
    direction: str = "vertical",
) -> LayoutResult:
    """root の血統子孫全員を対象に LayoutResult を計算する (SP-02, 粗い版)。"""
    options = display_options or DisplayOptions()
    lineage = frozenset(lineage_surnames) if lineage_surnames is not None else frozenset(
        {root.primary_name.surname} if root.primary_name.surname else set()
    )

    generations = assign_generations(db, roots=[root])
    for handle in list(generations):
        for spouse in db.spouses(db.people[handle]):
            if spouse.handle not in generations:
                generations[spouse.handle] = generations[handle]

    views: dict[str, PersonView] = {
        handle: build_person_view(
            db,
            db.people[handle],
            lineage_surnames=lineage,
            calendar=calendar,
            focus_person_handle=focus_person_handle,
        )
        for handle in generations
    }
    sizes: dict[str, NodeSize] = {
        handle: estimate_node_size(view, options) for handle, view in views.items()
    }

    context = _Context(db=db, sizes=sizes)
    _subtree_width(context, root)
    _assign_positions(context, root, 0.0)

    generation_height: dict[int, float] = {}
    for handle, gen in generations.items():
        generation_height[gen] = max(generation_height.get(gen, 0.0), sizes[handle].height)
    generation_y: dict[int, float] = {}
    cursor_y = 0.0
    for gen in sorted(generation_height):
        generation_y[gen] = cursor_y
        cursor_y += generation_height[gen] + GENERATION_GAP

    order_counters: dict[int, int] = {}
    nodes: list[PersonNode] = []
    for handle in sorted(generations, key=lambda h: (generations[h], context.x_position[h])):
        gen = generations[handle]
        order = order_counters.get(gen, 0)
        order_counters[gen] = order + 1
        size = sizes[handle]
        nodes.append(
            PersonNode(
                handle=handle,
                generation=gen,
                order_in_generation=order,
                x=context.x_position[handle],
                y=generation_y[gen],
                width=size.width,
                height=size.height,
                view=views[handle],
            )
        )

    included = set(generations)
    marriage_edges: list[MarriageEdge] = []
    child_edges: list[ChildEdge] = []
    for family in db.families.values():
        father = family.father_handle
        mother = family.mother_handle
        parent_gen = generations.get(father) if father in included else None
        if parent_gen is None:
            parent_gen = generations.get(mother) if mother in included else None
        if parent_gen is None:
            continue  # このレイアウトの対象範囲外の family

        if father in included and mother in included:
            start_x = (_center_x(context, father) + _center_x(context, mother)) / 2
        elif father in included:
            start_x = _center_x(context, father)
        elif mother in included:
            start_x = _center_x(context, mother)
        else:
            continue

        if father in included and mother in included:
            marriage_edges.append(
                MarriageEdge(
                    family_handle=family.handle,
                    husband_handle=father,
                    wife_handle=mother,
                    midpoint_x=start_x,
                    y=generation_y[parent_gen] + generation_height[parent_gen] / 2,
                )
            )

        parent_handles = [h for h in (father, mother) if h in included]

        parent_bottom = generation_y[parent_gen] + generation_height[parent_gen]
        bar_y = parent_bottom + GENERATION_GAP / 2
        for child_ref in family.children:
            if child_ref.person_handle not in included:
                continue
            child_gen = generations[child_ref.person_handle]
            child_x = _center_x(context, child_ref.person_handle)
            child_top = generation_y[child_gen]
            relation = (
                "adopted"
                if child_ref.frel == "Adopted" or child_ref.mrel == "Adopted"
                else "birth"
            )
            child_edges.append(
                ChildEdge(
                    family_handle=family.handle,
                    child_handle=child_ref.person_handle,
                    parent_handles=parent_handles,
                    relation=relation,
                    points=[
                        (start_x, parent_bottom),
                        (start_x, bar_y),
                        (child_x, bar_y),
                        (child_x, child_top),
                    ],
                )
            )

    auxiliary_nodes = _build_auxiliary_nodes(
        context, views, sizes, generations, generation_y, included, calendar, lineage, options
    )

    return LayoutResult(
        direction=direction,
        nodes=nodes,
        marriage_edges=marriage_edges,
        child_edges=child_edges,
        auxiliary_nodes=auxiliary_nodes,
    )


def _build_auxiliary_nodes(
    context: _Context,
    views: dict[str, PersonView],
    sizes: dict[str, NodeSize],
    generations: dict[str, int],
    generation_y: dict[int, float],
    included: set[str],
    calendar: Calendar,
    lineage: frozenset[str],
    options: DisplayOptions,
) -> list[PersonNode]:
    """婚入配偶者の実親を、その配偶者の直上に補助ノードとして配置する (SP-02-06)。"""
    db = context.db
    result: list[PersonNode] = []
    seen: set[str] = set()
    for handle in included:
        person = db.people[handle]
        if not person.childof:
            continue  # 血統側の人物、または実親不明の婚入配偶者
        for father, mother, _frel, _mrel in db.parents(person):
            for parent in (father, mother):
                if parent is None or parent.handle in included or parent.handle in seen:
                    continue
                seen.add(parent.handle)
                view = build_person_view(
                    db,
                    parent,
                    lineage_surnames=lineage,
                    calendar=calendar,
                    focus_person_handle=None,
                )
                size = estimate_node_size(view, options)
                gen = generations[handle]
                result.append(
                    PersonNode(
                        handle=parent.handle,
                        generation=gen,
                        order_in_generation=-1,
                        x=_center_x(context, handle) - size.width / 2,
                        y=generation_y[gen] - AUXILIARY_OFFSET - size.height,
                        width=size.width,
                        height=size.height,
                        view=view,
                    )
                )
    return result
