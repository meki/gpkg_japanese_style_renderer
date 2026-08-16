"""自動レイアウト計算 (SP-02, 粗い版。ノード重なり・エッジ交差の解消は Phase 6)。

処理の流れ:

1. `root` の血統子孫全員を `model.graph.assign_generations` の世代割当で対象人物
   とする。配偶者は各人物に隣接して配置するため、対象集合へ追加で取り込む。
2. 各人物の抽象寸法を `layout.metrics.estimate_node_size` で見積もる。生没年
   (date_column) は罫線ボックス (frame) には含まれず、frame の外側に確保する
   別領域として扱う (SP-03-06)。
3. `db.children()` (生年昇順) を用いて部分木の占有幅をボトムアップで計算し
   (`_subtree_width`)、親を子の中央に揃える形でトップダウンに x 座標を確定する
   (`_assign_positions`)。配偶者は人物のすぐ隣に配置し、家系側の人物を先
   (＝抽象座標の x が小さい側) に置く。占有幅には date_column_width を含める
   (隣接ノードと日付列が重ならないようにするため)。
4. 世代ごとの y 座標は、その世代で最も高いノード (frame と日付列のうち大きい方)
   に合わせた行として確定する (上揃え)。
5. 両親が揃って対象集合に含まれる family から夫婦連結線 (MarriageEdge) を、
   family の子のうち対象集合に含まれる人物へ親子接続線 (ChildEdge) を生成する。
   これらの Y 座標は「その世代で最も高いノード」ではなく、実際に連結する
   人物自身の frame の高さから求める (世代内の他ノードの高さに引きずられて
   線がボックスから乖離しないようにするため)。
6. 配偶者の実親が判明していれば、その配偶者の直上に補助ノード (auxiliary_nodes)
   として追加し、通常の親子接続と同様に MarriageEdge / ChildEdge も生成する
   (SP-02-06)。補助ノードは幅計算・重なり回避の対象に含めない。

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
    x_position: dict[str, float] = field(default_factory=dict)  # 各人物の「セル」の左端 x

    def frame_left(self, handle: str) -> float:
        """罫線ボックス (frame) 自身の左端。日付列はセルの中で frame より外側
        (抽象座標では小さい x 側。画面表示ではミラーにより frame の右隣になる)
        に確保するため、セル左端に date_column_width を足した位置になる。"""
        return self.x_position[handle] + self.sizes[handle].date_column_width

    def frame_center_x(self, handle: str) -> float:
        return self.frame_left(handle) + self.sizes[handle].frame_width / 2


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

    # 世代の行の高さは、(frame の高さ+顔写真の高さ) と日付列の高さのうち
    # 大きい方で決める。frame 自体は日付の長さに引きずられないが
    # (metrics.py 参照)、日付列や顔写真が frame より高くなる場合に次の世代と
    # 重ならないだけの余白は必要になる。顔写真は frame の直下に続けて配置する
    # ため、frame の高さと足し合わせる (日付列は frame と横並びのため足さない)。
    generation_height: dict[int, float] = {}
    for handle, gen in generations.items():
        occupied = max(
            sizes[handle].height + sizes[handle].photo_height, sizes[handle].date_column_height
        )
        generation_height[gen] = max(generation_height.get(gen, 0.0), occupied)
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
                x=context.frame_left(handle),
                y=generation_y[gen],
                width=size.frame_width,
                height=size.height,
                date_column_width=size.date_column_width,
                photo_height=size.photo_height,
                view=views[handle],
            )
        )

    included = set(generations)
    marriage_edges: list[MarriageEdge] = []
    child_edges: list[ChildEdge] = []
    for family in db.families.values():
        father = family.father_handle
        mother = family.mother_handle
        father_in = father is not None and father in included
        mother_in = mother is not None and mother in included
        if not father_in and not mother_in:
            continue  # このレイアウトの対象範囲外の family

        if father_in:
            assert father is not None
            parent_gen = generations[father]
        else:
            assert mother is not None
            parent_gen = generations[mother]

        if father_in and mother_in:
            assert father is not None and mother is not None
            start_x = (context.frame_center_x(father) + context.frame_center_x(mother)) / 2
            # 世代内の他ノードの高さに引きずられないよう、実際に連結する2人
            # 自身の frame の高さ (の小さい方) から Y を決める。こうすると
            # 水平線は必ず両者の frame の内側を通る。
            common_height = min(sizes[father].height, sizes[mother].height)
            start_y = generation_y[parent_gen] + common_height / 2
            marriage_edges.append(
                MarriageEdge(
                    family_handle=family.handle,
                    husband_handle=father,
                    wife_handle=mother,
                    midpoint_x=start_x,
                    y=start_y,
                )
            )
        elif father_in:
            assert father is not None
            start_x = context.frame_center_x(father)
            # 単親の場合、線は frame の下端ではなく (顔写真があれば) その下端
            # から降ろす。frame の直後に写真を挟んで描画するため。
            start_y = generation_y[parent_gen] + sizes[father].height + sizes[father].photo_height
        else:
            assert mother is not None
            start_x = context.frame_center_x(mother)
            start_y = generation_y[parent_gen] + sizes[mother].height + sizes[mother].photo_height

        parent_handles = [h for h in (father, mother) if h is not None and h in included]
        bar_y = generation_y[parent_gen] + generation_height[parent_gen] + GENERATION_GAP / 2
        for child_ref in family.children:
            if child_ref.person_handle not in included:
                continue
            child_gen = generations[child_ref.person_handle]
            child_x = context.frame_center_x(child_ref.person_handle)
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
                        (start_x, start_y),
                        (start_x, bar_y),
                        (child_x, bar_y),
                        (child_x, child_top),
                    ],
                )
            )

    aux_nodes, aux_marriage_edges, aux_child_edges = _build_auxiliary_data(
        context, generations, generation_y, included, calendar, lineage, options
    )

    return LayoutResult(
        direction=direction,
        nodes=nodes,
        marriage_edges=marriage_edges + aux_marriage_edges,
        child_edges=child_edges + aux_child_edges,
        auxiliary_nodes=aux_nodes,
    )


def _build_auxiliary_data(
    context: _Context,
    generations: dict[str, int],
    generation_y: dict[int, float],
    included: set[str],
    calendar: Calendar,
    lineage: frozenset[str],
    options: DisplayOptions,
) -> tuple[list[PersonNode], list[MarriageEdge], list[ChildEdge]]:
    """婚入配偶者の実親を、その配偶者の直上に補助ノードとして配置し (SP-02-06)、
    通常の親子接続と同様に MarriageEdge / ChildEdge も生成する。

    補助ノードに接続線を生成しない実装だと、対象人物の実親がメインの木の外に
    いるケース (例えば起点人物の配偶者の親) で人物ノードだけが宙に浮いて表示
    され、実データでの目視確認時に判明した。
    """
    db = context.db
    nodes: list[PersonNode] = []
    marriage_edges: list[MarriageEdge] = []
    child_edges: list[ChildEdge] = []
    node_by_handle: dict[str, PersonNode] = {}

    def get_or_create(parent: Person, child_handle: str) -> PersonNode:
        existing = node_by_handle.get(parent.handle)
        if existing is not None:
            return existing
        view = build_person_view(
            db, parent, lineage_surnames=lineage, calendar=calendar, focus_person_handle=None
        )
        size = estimate_node_size(view, options)
        gen = generations[child_handle]
        # aux_bottom は補助ノード一式 (frame + 顔写真があればその下端まで) の
        # 下端。顔写真がある場合は frame をその分だけ上へずらして確保する。
        aux_bottom = generation_y[gen] - AUXILIARY_OFFSET
        node = PersonNode(
            handle=parent.handle,
            generation=gen,
            order_in_generation=-1,
            x=context.frame_center_x(child_handle) - size.frame_width / 2,
            y=aux_bottom - size.photo_height - size.height,
            width=size.frame_width,
            height=size.height,
            date_column_width=size.date_column_width,
            photo_height=size.photo_height,
            view=view,
        )
        node_by_handle[parent.handle] = node
        nodes.append(node)
        return node

    for handle in included:
        person = db.people[handle]
        if not person.childof:
            continue  # 血統側の人物、または実親不明の婚入配偶者
        for father, mother, frel, mrel in db.parents(person):
            father_needs_aux = father is not None and father.handle not in included
            mother_needs_aux = mother is not None and mother.handle not in included
            if not father_needs_aux and not mother_needs_aux:
                continue  # 両親ともすでにメインツリーに含まれる (通常の接続線で描画済み)

            father_node = get_or_create(father, handle) if father_needs_aux else None
            mother_node = get_or_create(mother, handle) if mother_needs_aux else None
            relation = "adopted" if frel == "Adopted" or mrel == "Adopted" else "birth"

            if father_node is not None and mother_node is not None:
                aux_bottom = generation_y[generations[handle]] - AUXILIARY_OFFSET
                common_height = min(father_node.height, mother_node.height)
                start_y = aux_bottom - common_height / 2
                start_x = (
                    father_node.x
                    + father_node.width / 2
                    + mother_node.x
                    + mother_node.width / 2
                ) / 2
                marriage_edges.append(
                    MarriageEdge(
                        family_handle=f"aux-{father.handle}-{mother.handle}",
                        husband_handle=father.handle,
                        wife_handle=mother.handle,
                        midpoint_x=start_x,
                        y=start_y,
                    )
                )
                parent_handles = [father.handle, mother.handle]
            else:
                solo = father_node if father_node is not None else mother_node
                assert solo is not None
                start_x = solo.x + solo.width / 2
                start_y = solo.y + solo.height + solo.photo_height
                parent_handles = [solo.handle]

            child_gen = generations[handle]
            child_x = context.frame_center_x(handle)
            child_top = generation_y[child_gen]
            bar_y = start_y + (child_top - start_y) / 2
            child_edges.append(
                ChildEdge(
                    family_handle=f"aux-child-{handle}",
                    child_handle=handle,
                    parent_handles=parent_handles,
                    relation=relation,
                    points=[
                        (start_x, start_y),
                        (start_x, bar_y),
                        (child_x, bar_y),
                        (child_x, child_top),
                    ],
                )
            )

    return nodes, marriage_edges, child_edges
