from __future__ import annotations

from gpkg_jsr.format.name_rules import infer_lineage_surnames
from gpkg_jsr.gramps.gpkg_reader import GrampsDatabase
from gpkg_jsr.model.view import build_person_view


def _load(minimal_family_xml_bytes: bytes) -> GrampsDatabase:
    return GrampsDatabase.load_xml_bytes(minimal_family_xml_bytes)


def _lineage(db: GrampsDatabase) -> frozenset[str]:
    return infer_lineage_surnames(db.people.values())


def test_every_person_in_fixture_builds_without_error(minimal_family_xml_bytes: bytes) -> None:
    """フィクスチャ全人物 (欠損データ・孤立人物を含む) が例外なく PersonView になること。

    実データ (山田家系図.gpkg, 136名) での同等の検証は本ワークツリーには
    __example_data/ が存在しないため実施できない (docs/90_Onboarding.md 参照)。
    このテストはその代替として、フィクスチャに含まれる既知のエッジケースを
    網羅的に確認する。
    """
    db = _load(minimal_family_xml_bytes)
    lineage = _lineage(db)
    for calendar in ("western", "wareki"):
        for person in db.people.values():
            view = build_person_view(db, person, lineage_surnames=lineage, calendar=calendar)
            assert view is not None


class TestBasicFields:
    def test_western_calendar(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        jiro = db.people["_p0003"]
        view = build_person_view(db, jiro, lineage_surnames=_lineage(db), calendar="western")

        assert view.surname == "山田"
        assert view.given_name == "次郎"
        assert view.surname_kana == "やまだ"
        assert view.given_name_kana == "じろう"
        assert view.former_surname is None
        assert view.is_spouse_in is False
        assert view.birth_order_label == "長男"
        assert view.blood_type is None
        assert view.is_deceased is False
        assert view.has_photo is False
        assert view.notes == []
        assert view.is_focus_person is False
        assert view.gender == "M"
        assert view.birth_date_display is not None
        assert view.birth_date_display.calendar == "western"
        assert view.birth_date_display.text == "1875年6月1日生"
        assert view.death_date_display is None

    def test_wareki_calendar(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        jiro = db.people["_p0003"]
        view = build_person_view(db, jiro, lineage_surnames=_lineage(db), calendar="wareki")

        assert view.birth_date_display is not None
        assert view.birth_date_display.calendar == "wareki"
        assert view.birth_date_display.text == "明治八年六月一日生"

    def test_focus_person(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        jiro = db.people["_p0003"]
        view = build_person_view(
            db, jiro, lineage_surnames=_lineage(db), focus_person_handle="_p0003"
        )
        assert view.is_focus_person is True

        taro = db.people["_p0001"]
        other_view = build_person_view(
            db, taro, lineage_surnames=_lineage(db), focus_person_handle="_p0003"
        )
        assert other_view.is_focus_person is False


class TestAdoptionAndFormerSurname:
    def test_adopted_person_uses_current_surname_for_spouse_in_check(
        self, minimal_family_xml_bytes: bytes
    ) -> None:
        db = _load(minimal_family_xml_bytes)
        saburo = db.people["_p0004"]
        view = build_person_view(db, saburo, lineage_surnames=_lineage(db))

        assert view.surname == "山田"
        assert view.former_surname == "鈴木"
        assert view.is_spouse_in is False  # 現姓が家系姓と一致するため
        assert view.birth_order_label == "次男"
        assert view.has_photo is True
        assert view.notes == ["実父 鈴木源蔵"]


class TestSpouseIn:
    def test_spouse_in_person(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        saki = db.people["_p0005"]
        view = build_person_view(db, saki, lineage_surnames=_lineage(db))
        assert view.surname == "田中"
        assert view.is_spouse_in is True

    def test_person_with_blood_type_attribute(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        ume = db.people["_p0007"]
        view = build_person_view(db, ume, lineage_surnames=_lineage(db))
        assert view.blood_type == "A型"


class TestNamelessPerson:
    def test_nameless_isolated_person(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        unknown = db.people["_p0009"]
        view = build_person_view(db, unknown, lineage_surnames=_lineage(db))
        assert view.surname == ""
        assert view.given_name == ""
        assert view.is_spouse_in is True
        assert view.gender == "U"
        assert view.birth_date_display is None
        assert view.death_date_display is None


class TestDeathDisplay:
    def test_before_modifier_with_wareki(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        taro = db.people["_p0001"]
        view = build_person_view(db, taro, lineage_surnames=_lineage(db), calendar="wareki")

        assert view.birth_date_display is not None
        assert view.birth_date_display.calendar == "wareki"
        # 1850 年は太陽暦採用 (1873) 以前のため月日を表示しない (ADR-03)。
        assert view.birth_date_display.text == "嘉永三年生"

        assert view.death_date_display is not None
        assert view.death_date_display.calendar == "wareki"
        assert view.death_date_display.text == "大正九年以前没"
        assert view.is_deceased is True


class TestWarekiFallback:
    def test_datestr_falls_back_to_western(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        ume = db.people["_p0007"]
        view = build_person_view(db, ume, lineage_surnames=_lineage(db), calendar="wareki")

        assert view.birth_date_display is not None
        assert view.birth_date_display.calendar == "western"
        assert view.birth_date_display.text == "幕末生まれ、詳細不明生"

    def test_daterange_falls_back_to_western(self, minimal_family_xml_bytes: bytes) -> None:
        db = _load(minimal_family_xml_bytes)
        itsuko = db.people["_p0008"]
        view = build_person_view(db, itsuko, lineage_surnames=_lineage(db), calendar="wareki")

        assert view.birth_date_display is not None
        assert view.birth_date_display.calendar == "western"
        assert view.birth_date_display.text == "1903年〜1905年生"
