from __future__ import annotations

from gpkg_jsr.gramps.gpkg_reader import GrampsDatabase
from gpkg_jsr.layout.engine import build_layout
from gpkg_jsr.layout.types import LayoutResult

# 補助ノード (SP-02-06: 婚入配偶者の実家併記) をテストするための小さな専用フィクスチャ。
# 花子 (太郎の妻) には実父 源一 が判明している、という最小構成。
_SPOUSE_WITH_KNOWN_PARENT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE database PUBLIC "-//Gramps//DTD Gramps XML 1.7.2//EN"
"http://gramps-project.org/xml/1.7.2/grampsxml.dtd">
<database xmlns="http://gramps-project.org/xml/1.7.2/">
  <header><created date="2026-08-15" version="6.0.8"/><researcher/></header>
  <people>
    <person handle="_p0001" id="I0001">
      <gender>M</gender>
      <name type="Birth Name"><first>太郎</first><surname>山田</surname></name>
      <parentin hlink="_f0001"/>
    </person>
    <person handle="_p0002" id="I0002">
      <gender>F</gender>
      <name type="Birth Name"><first>花子</first><surname>斎藤</surname></name>
      <childof hlink="_f0002"/>
      <parentin hlink="_f0001"/>
    </person>
    <person handle="_p0003" id="I0003">
      <gender>M</gender>
      <name type="Birth Name"><first>次郎</first><surname>山田</surname></name>
      <childof hlink="_f0001"/>
    </person>
    <person handle="_p0004" id="I0004">
      <gender>M</gender>
      <name type="Birth Name"><first>源一</first><surname>斎藤</surname></name>
      <parentin hlink="_f0002"/>
    </person>
  </people>
  <families>
    <family handle="_f0001" id="F0001">
      <rel type="Married"/>
      <father hlink="_p0001"/>
      <mother hlink="_p0002"/>
      <childref hlink="_p0003" frel="Birth" mrel="Birth"/>
    </family>
    <family handle="_f0002" id="F0002">
      <father hlink="_p0004"/>
      <childref hlink="_p0002" frel="Birth" mrel="Birth"/>
    </family>
  </families>
</database>
""".encode()


def _load(minimal_family_xml_bytes: bytes) -> GrampsDatabase:
    return GrampsDatabase.load_xml_bytes(minimal_family_xml_bytes)


def _handles(result: LayoutResult) -> set[str]:
    return {node.handle for node in result.nodes}


class TestBasicStructure:
    def test_all_bloodline_and_spouse_handles_are_present(
        self, minimal_family_xml_bytes: bytes
    ) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        result = build_layout(db, taro, lineage_surnames=frozenset({"山田"}))

        assert _handles(result) == {
            "_p0001",  # 太郎
            "_p0002",  # 花子
            "_p0003",  # 次郎
            "_p0004",  # 三郎
            "_p0005",  # 咲
            "_p0006",  # 四郎
            "_p0007",  # 梅
            "_p0008",  # 五子
            "_p0010",  # 六郎
        }
        # 血縁関係のない孤立人物は含まれない
        assert "_p0009" not in _handles(result)

    def test_all_nodes_have_positive_dimensions(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        result = build_layout(db, taro, lineage_surnames=frozenset({"山田"}))
        for node in result.nodes:
            assert node.width > 0
            assert node.height > 0

    def test_generation_assignment(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        result = build_layout(db, taro, lineage_surnames=frozenset({"山田"}))
        generation_by_handle = {node.handle: node.generation for node in result.nodes}

        assert generation_by_handle["_p0001"] == 0  # 太郎
        assert generation_by_handle["_p0002"] == 0  # 花子 (太郎の配偶者)
        assert generation_by_handle["_p0003"] == 1  # 次郎
        assert generation_by_handle["_p0004"] == 1  # 三郎
        assert generation_by_handle["_p0005"] == 1  # 咲 (次郎の配偶者)
        assert generation_by_handle["_p0007"] == 1  # 梅 (次郎の配偶者)
        assert generation_by_handle["_p0006"] == 2  # 四郎
        assert generation_by_handle["_p0010"] == 2  # 六郎
        assert generation_by_handle["_p0008"] == 2  # 五子

    def test_lineage_surnames_defaults_to_roots_own_surname(
        self, minimal_family_xml_bytes: bytes
    ) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        # lineage_surnames を省略しても例外なく計算でき、root の姓が家系姓として
        # 扱われるため root 自身は is_spouse_in=False になる。
        result = build_layout(db, taro)
        by_handle = {node.handle: node for node in result.nodes}
        assert by_handle["_p0001"].view.is_spouse_in is False
        assert by_handle["_p0002"].view.is_spouse_in is True  # 花子 (斎藤)

    def test_default_calendar_is_wareki(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        result = build_layout(db, taro, lineage_surnames=frozenset({"山田"}))
        jiro = next(n for n in result.nodes if n.handle == "_p0003")
        assert jiro.view.birth_date_display is not None
        assert jiro.view.birth_date_display.calendar == "wareki"

    def test_direction_is_passed_through(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        result = build_layout(
            db, taro, lineage_surnames=frozenset({"山田"}), direction="horizontal"
        )
        assert result.direction == "horizontal"


class TestEdges:
    def test_marriage_edge_count(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        result = build_layout(db, taro, lineage_surnames=frozenset({"山田"}))
        # F0001 (太郎/花子), F0002 (次郎/咲), F0003 (次郎/梅) の 3 組
        assert len(result.marriage_edges) == 3
        family_handles = {edge.family_handle for edge in result.marriage_edges}
        assert family_handles == {"_f0001", "_f0002", "_f0003"}

    def test_child_edge_count_and_relations(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        result = build_layout(db, taro, lineage_surnames=frozenset({"山田"}))
        # F0001:次郎,三郎 / F0002:四郎,六郎 / F0003:五子 = 合計5本
        assert len(result.child_edges) == 5

        relation_by_child = {edge.child_handle: edge.relation for edge in result.child_edges}
        assert relation_by_child["_p0003"] == "birth"  # 次郎
        assert relation_by_child["_p0004"] == "adopted"  # 三郎 (養子)
        assert relation_by_child["_p0006"] == "birth"  # 四郎
        assert relation_by_child["_p0010"] == "birth"  # 六郎
        assert relation_by_child["_p0008"] == "birth"  # 五子

    def test_child_edge_parent_handles(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        result = build_layout(db, taro, lineage_surnames=frozenset({"山田"}))
        edge = next(e for e in result.child_edges if e.child_handle == "_p0003")
        assert set(edge.parent_handles) == {"_p0001", "_p0002"}  # 太郎・花子

    def test_child_edge_is_a_three_segment_polyline(
        self, minimal_family_xml_bytes: bytes
    ) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        result = build_layout(db, taro, lineage_surnames=frozenset({"山田"}))
        edge = next(e for e in result.child_edges if e.child_handle == "_p0003")
        assert len(edge.points) == 4
        (x0, _y0), (x1, y1), (x2, y2), (x3, _y3) = edge.points
        assert x0 == x1  # 始点から垂直に下降
        assert y1 == y2  # 兄弟バーは水平
        assert x2 == x3  # 子へ向けて垂直に下降


class TestOrdering:
    def test_elder_sibling_has_smaller_x(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        result = build_layout(db, taro, lineage_surnames=frozenset({"山田"}))
        by_handle = {node.handle: node for node in result.nodes}
        # 次郎 (1875年生) は三郎 (1878年生) より年長 -> x が小さい (SP-02-03)
        assert by_handle["_p0003"].x < by_handle["_p0004"].x

    def test_lineage_person_precedes_spouse_in_x(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        result = build_layout(db, taro, lineage_surnames=frozenset({"山田"}))
        by_handle = {node.handle: node for node in result.nodes}
        # 次郎 (家系側) は配偶者の咲・梅より x が小さい
        assert by_handle["_p0003"].x < by_handle["_p0005"].x
        assert by_handle["_p0003"].x < by_handle["_p0007"].x


class TestAuxiliaryNodes:
    def test_spouse_known_parent_becomes_auxiliary_node(self) -> None:
        db = GrampsDatabase.load_xml_bytes(_SPOUSE_WITH_KNOWN_PARENT_XML)
        taro = db.people["_p0001"]
        result = build_layout(db, taro, lineage_surnames=frozenset({"山田"}))

        # 主要ノードには血統 (太郎・次郎) と配偶者 (花子) のみが含まれる
        assert _handles(result) == {"_p0001", "_p0002", "_p0003"}

        assert len(result.auxiliary_nodes) == 1
        aux = result.auxiliary_nodes[0]
        assert aux.handle == "_p0004"  # 源一 (花子の実父)
        assert aux.view.given_name == "源一"

        hanako = next(n for n in result.nodes if n.handle == "_p0002")
        # 補助ノードは配偶者の直上に配置される
        assert aux.y < hanako.y
