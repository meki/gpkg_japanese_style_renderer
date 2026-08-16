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
    width: float  # 配置に使う占有幅 (frame_width + date_column_width)
    height: float  # 罫線ボックス (frame) 自体の高さ。生没年・写真はここに含めない
    frame_width: float  # 罫線で囲むノード本体の幅
    date_column_width: float  # 生没年表記用に frame の外側へ確保する列の幅 (0 なら無し)
    date_column_height: float  # 生没年表記列自体の高さ (行間の確保に使う。0 なら無し)
    photo_height: float = 0.0  # 顔写真用に frame の外側 (下) へ確保する高さ (0 なら無し)


class PersonNode(BaseModel):
    handle: str
    generation: int
    order_in_generation: int
    x: float
    y: float
    width: float  # 罫線ボックス (frame) の幅。date_column_width は含まない
    height: float
    date_column_width: float  # 生没年列の幅。描画層は x+width の外側 (画面表示では右隣) に配置する
    photo_height: float = 0.0  # 顔写真列の高さ。描画層は y+height の外側 (下) に配置する
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
    parent_handles: list[str]  # 1件 (単親) または 2件 (両親)。DF-01-04 参照
    relation: str  # "birth" | "adopted"
    points: list[tuple[float, float]]


class LayoutResult(BaseModel):
    version: int = 1
    direction: str = "vertical"  # "vertical" | "horizontal" (SP-02-07)
    nodes: list[PersonNode] = []
    marriage_edges: list[MarriageEdge] = []
    child_edges: list[ChildEdge] = []
    auxiliary_nodes: list[PersonNode] = []
