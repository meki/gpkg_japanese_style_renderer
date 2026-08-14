from __future__ import annotations

import pytest

from gpkg_jsr.gramps.gpkg_reader import GrampsDatabase
from gpkg_jsr.model.graph import (
    assign_generations,
    reachable_ancestors,
    reachable_descendants,
    reachable_people,
)


def _load(minimal_family_xml_bytes: bytes) -> GrampsDatabase:
    return GrampsDatabase.load_xml_bytes(minimal_family_xml_bytes)


class TestAssignGenerations:
    def test_single_bloodline_root(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        generations = assign_generations(db, roots=[taro])
        assert generations == {
            "_p0001": 0,  # 太郎
            "_p0003": 1,  # 次郎
            "_p0004": 1,  # 三郎 (養子)
            "_p0006": 2,  # 四郎
            "_p0010": 2,  # 六郎
            "_p0008": 2,  # 五子
        }

    def test_default_roots_include_spouse_in_people(
        self, minimal_family_xml_bytes: bytes
    ) -> None:
        db = _load(minimal_family_xml_bytes)
        generations = assign_generations(db)
        # db.roots() には婚入配偶者 (咲・梅) も含まれるため、次郎とその配偶者との
        # 子は最短経路 (配偶者経由の世代 0 起点) が優先され、血統をたどった場合の
        # 世代 2 ではなく世代 1 に「潰れる」(SP-02-01 の既知の制約を参照)。
        assert generations["_p0003"] == 1  # 次郎 (太郎の子)
        assert generations["_p0006"] == 1  # 四郎 (次郎の子、本来は世代2相当)
        assert generations["_p0010"] == 1
        assert generations["_p0008"] == 1
        assert set(generations.values()) == {0, 1}

    def test_isolated_person_is_generation_zero(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        generations = assign_generations(db)
        assert generations["_p0009"] == 0


class TestReachableSets:
    def test_reachable_descendants_from_taro(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        result = reachable_descendants(db, taro)
        assert result == {"_p0001", "_p0003", "_p0004", "_p0006", "_p0010", "_p0008"}

    def test_reachable_descendants_leaf_is_only_itself(
        self, minimal_family_xml_bytes: bytes
    ) -> None:
        db = _load(minimal_family_xml_bytes)
        itsuko = db.people["_p0008"]
        assert reachable_descendants(db, itsuko) == {"_p0008"}

    def test_reachable_ancestors_from_grandchild(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        shiro = db.people["_p0006"]  # 四郎: 次郎 x 咲 の子
        result = reachable_ancestors(db, shiro)
        assert result == {"_p0006", "_p0003", "_p0005", "_p0001", "_p0002"}

    def test_reachable_ancestors_handles_multiple_childof(
        self, minimal_family_xml_bytes: bytes
    ) -> None:
        db = _load(minimal_family_xml_bytes)
        saburo = db.people["_p0004"]  # 三郎: 太郎/花子 の養子
        result = reachable_ancestors(db, saburo)
        assert result == {"_p0004", "_p0001", "_p0002"}

    def test_reachable_people_both_directions(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        jiro = db.people["_p0003"]  # 次郎: 太郎/花子の子であり、四郎/六郎/五子の親
        result = reachable_people(db, jiro, "both")
        assert result == {"_p0003", "_p0001", "_p0002", "_p0006", "_p0010", "_p0008"}

    def test_reachable_people_invalid_direction_raises(
        self, minimal_family_xml_bytes: bytes
    ) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        with pytest.raises(ValueError):
            reachable_people(db, taro, "sideways")  # type: ignore[arg-type]
