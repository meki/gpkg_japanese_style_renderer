"""LayoutResult 等、Python とブラウザ描画層の唯一の契約となる型定義 (DF-01, AD-01-03)。

座標は常に「世代軸 = 縦方向 (y が増えるほど後の世代)」の抽象座標系で表現する。
横書き表示 (RQ-02-08) への変換は描画直前にブラウザ側で行い、ここでは行わない
(SP-02-07)。

兄弟の並び順 (RQ-02-03: 年長者を右に配置) についても同様に抽象順序のみを
`order_in_generation` / x 座標の昇順で表し、実際に右→左のどちらへ描画するかは
描画層の責務とする。x の昇順 = 年長者から並べた出現順 (0 が最年長) であり、
最終的な日本式表示では x=0 が画面上「最も右」に来るよう描画層でミラーする。
"""
from __future__ import annotations

from pydantic import BaseModel

from gpkg_jsr.model.view import PersonView


class DisplayOptions(BaseModel):
    """表示項目トグル (SP-03-12, DF-03-03)。ノード寸法推定にも用いる。"""

    show_ruby: bool = True
    show_birth_order: bool = True
    show_dates: bool = True
    show_photos: bool = True
    show_former_surname: bool = True


class NodeSize(BaseModel):
    width: float
    height: float


class PersonNode(BaseModel):
    handle: str
    generation: int
    order_in_generation: int
    x: float
    y: float
    width: float
    height: float
    view: PersonView


class MarriageEdge(BaseModel):
    family_handle: str
    husband_handle: str
    wife_handle: str
    midpoint_x: float
    y: float


class ChildEdge(BaseModel):
    family_handle: str
    child_handle: str
    relation: str  # "birth" | "adopted"
    points: list[tuple[float, float]]


class LayoutResult(BaseModel):
    version: int = 1
    direction: str = "vertical"  # "vertical" | "horizontal" (SP-02-07)
    nodes: list[PersonNode] = []
    marriage_edges: list[MarriageEdge] = []
    child_edges: list[ChildEdge] = []
    auxiliary_nodes: list[PersonNode] = []
