from __future__ import annotations

from gpkg_jsr.format.name_rules import former_surname, infer_lineage_surnames, is_spouse_in
from gpkg_jsr.gramps.gpkg_reader import GrampsDatabase


def _load(minimal_family_xml_bytes: bytes) -> GrampsDatabase:
    return GrampsDatabase.load_xml_bytes(minimal_family_xml_bytes)


def test_infer_lineage_surnames(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    # 山田 (6名) が唯一の家系姓。斎藤/田中/佐藤 (各1名) は閾値未満で対象外。
    assert infer_lineage_surnames(db.people.values()) == frozenset({"山田"})


def test_is_spouse_in(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    lineage = infer_lineage_surnames(db.people.values())
    jiro = db.people["_p0003"]  # 山田次郎
    hanako = db.people["_p0002"]  # 斎藤花子 (太郎の妻)
    assert is_spouse_in(jiro, lineage) is False
    assert is_spouse_in(hanako, lineage) is True


def test_is_spouse_in_with_no_name_treated_as_spouse_in(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    lineage = infer_lineage_surnames(db.people.values())
    unknown = db.people["_p0009"]
    assert is_spouse_in(unknown, lineage) is True


def test_former_surname_present(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    saburo = db.people["_p0004"]
    assert former_surname(saburo) == "鈴木"


def test_former_surname_absent(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    jiro = db.people["_p0003"]
    assert former_surname(jiro) is None
