from __future__ import annotations

from gpkg_jsr.gramps.gpkg_reader import GrampsDatabase


def _load(minimal_family_xml_bytes: bytes) -> GrampsDatabase:
    return GrampsDatabase.load_xml_bytes(minimal_family_xml_bytes)


def test_counts(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    assert len(db.people) == 10
    assert len(db.families) == 3
    assert len(db.events) == 10
    assert len(db.objects) == 1
    assert len(db.notes) == 1


def test_adoption_uses_adopted_relation(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    saburo = db.people["_p0004"]
    [(father, mother, frel, mrel)] = db.parents(saburo)
    assert father.id == "I0001"
    assert mother.id == "I0002"
    assert frel == "Adopted"
    assert mrel == "Adopted"


def test_former_surname_from_also_known_as(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    saburo = db.people["_p0004"]
    assert saburo.display_name() == "山田 三郎"
    alt = saburo.alt_names
    assert len(alt) == 1
    assert alt[0].surname == "鈴木"
    assert alt[0].type == "Also Known As"


def test_birth_relation_default_is_birth(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    jiro = db.people["_p0003"]
    [(_father, _mother, frel, mrel)] = db.parents(jiro)
    assert frel == "Birth"
    assert mrel == "Birth"


def test_remarriage_multiple_spouses(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    jiro = db.people["_p0003"]
    assert len(jiro.parentin) == 2
    spouse_ids = {s.id for s in db.spouses(jiro)}
    assert spouse_ids == {"I0005", "I0007"}


def test_family_without_rel_type_is_none(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    fam = db.families["_f0003"]
    assert fam.rel_type is None


def test_children_sorted_by_birth_ascending(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    jiro = db.people["_p0003"]
    children = db.children(jiro)
    # I0008 (五子) の生年は daterange のみで表現されており、GDate.year は
    # dateval 由来の日付にしか設定されないため、生年不明として末尾に回る。
    assert [c.id for c in children] == ["I0006", "I0010", "I0008"]


def test_roots_are_people_without_childof(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    root_ids = {p.id for p in db.roots()}
    assert root_ids == {"I0001", "I0002", "I0005", "I0007", "I0009"}


def test_nameless_person_has_fallback_display_name(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    unknown = db.people["_p0009"]
    assert unknown.display_name() == "(名前不明)"
    assert unknown.gender == "U"


def test_notes_for_person(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    saburo = db.people["_p0004"]
    assert db.notes_for(saburo) == ["実父 鈴木源蔵"]


def test_media_object_metadata_without_archive(minimal_family_xml_bytes: bytes) -> None:
    db = _load(minimal_family_xml_bytes)
    saburo = db.people["_p0004"]
    assert saburo.objrefs == ["_o0001"]
    media = db.objects["_o0001"]
    assert media.mime == "image/jpeg"
    assert media.src == "GrampsMedia/I0004.jpg"
    # load_xml_bytes() はアーカイブを扱わないため、実バイト列は取得できない
    assert db.photo_bytes(saburo) is None


class TestDateParsing:
    def test_full_date(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        d = db.birth_date(taro)
        assert d is not None
        assert (d.year, d.month, d.day) == (1850, 3, 5)

    def test_year_only(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        saburo = db.people["_p0004"]
        d = db.birth_date(saburo)
        assert d is not None
        assert (d.year, d.month, d.day) == (1878, None, None)

    def test_unknown_year_known_month_day(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        saki = db.people["_p0005"]
        d = db.birth_date(saki)
        assert d is not None
        assert (d.year, d.month, d.day) == (None, 4, 8)

    def test_about_modifier(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        hanako = db.people["_p0002"]
        d = db.birth_date(hanako)
        assert d is not None
        assert d.modifier == "about"
        assert "頃" in d.format_ja()

    def test_before_modifier_with_estimated_quality(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        d = db.death_date(taro)
        assert d is not None
        assert d.modifier == "before"
        assert d.quality == "estimated"
        assert "以前" in d.format_ja()
        assert db.is_deceased(taro) is True

    def test_datestr_freeform(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        ume = db.people["_p0007"]
        d = db.birth_date(ume)
        assert d is not None
        assert d.kind == "datestr"
        assert d.format_ja() == "幕末生まれ、詳細不明"

    def test_daterange(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        itsuko = db.people["_p0008"]
        d = db.birth_date(itsuko)
        assert d is not None
        assert d.kind == "daterange"
        assert d.start == (1903, None, None)
        assert d.stop == (1905, None, None)

    def test_no_death_event_means_not_deceased(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        jiro = db.people["_p0003"]
        assert db.is_deceased(jiro) is False
        assert db.death_date(jiro) is None
