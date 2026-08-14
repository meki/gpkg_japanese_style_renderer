"""Person -> PersonView への正規化 (SP-01, SP-03-01, DF-01-03)。

`PersonView` は画面描画に必要な情報だけを持つ、表示専用の正規化済みデータ
構造。Gramps 側のデータモデル (`handle`, `frel` 等) はここで吸収し、これより
上位のレイアウト層・描画層は `PersonView` の形しか意識しない (ADR-04)。
"""
from __future__ import annotations

from collections.abc import Set
from typing import Literal

from pydantic import BaseModel

from gpkg_jsr.format.kanji_number import kanji_number
from gpkg_jsr.format.name_rules import former_surname, is_spouse_in
from gpkg_jsr.format.wareki import format_wareki_year, is_pre_gregorian_adoption
from gpkg_jsr.gramps.gpkg_reader import GDate, GrampsDatabase, Person

Calendar = Literal["western", "wareki"]

_MODIFIER_SUFFIX = {"about": "頃", "before": "以前", "after": "以後"}


class DateDisplay(BaseModel):
    calendar: Calendar
    text: str


class PersonView(BaseModel):
    surname: str
    given_name: str
    surname_kana: str | None = None
    given_name_kana: str | None = None
    former_surname: str | None = None
    is_spouse_in: bool
    birth_order_label: str | None = None
    blood_type: str | None = None
    birth_date_display: DateDisplay | None = None
    death_date_display: DateDisplay | None = None
    is_deceased: bool
    has_photo: bool
    notes: list[str] = []
    is_focus_person: bool = False
    gender: str


def build_person_view(
    db: GrampsDatabase,
    person: Person,
    *,
    lineage_surnames: Set[str],
    calendar: Calendar = "wareki",
    focus_person_handle: str | None = None,
) -> PersonView:
    """Person を PersonView へ変換する (SP-01-04, SP-01-05, SP-01-06, SP-03-*)。"""
    name = person.primary_name
    birth = db.birth_date(person)
    death = db.death_date(person)

    return PersonView(
        surname=name.surname,
        given_name=name.first,
        surname_kana=person.get_attribute("姓(カナ)"),
        given_name_kana=person.get_attribute("名(カナ)"),
        former_surname=former_surname(person),
        is_spouse_in=is_spouse_in(person, lineage_surnames),
        birth_order_label=person.get_attribute("続柄"),
        blood_type=person.get_attribute("血液型"),
        birth_date_display=format_date_display(birth, calendar, "生"),
        death_date_display=format_date_display(death, calendar, "没"),
        is_deceased=db.is_deceased(person),
        has_photo=any(handle in db.objects for handle in person.objrefs),
        notes=db.notes_for(person),
        is_focus_person=person.handle == focus_person_handle,
        gender=person.gender,
    )


def format_date_display(date: GDate | None, calendar: Calendar, suffix: str) -> DateDisplay | None:
    """GDate を表示用テキストに変換する (SP-03-06, SP-04-04, SP-04-05)。"""
    if date is None:
        return None
    if calendar == "western":
        return DateDisplay(calendar="western", text=f"{date.format_ja()}{suffix}")

    wareki_text = _wareki_text(date)
    if wareki_text is None:
        # 和暦へ変換できない日付表現 (datestr・daterange・datespan・年不明) は
        # 西暦表示にフォールバックする (SP-04-05)。情報を隠すより正確な原文を
        # 見せる方を優先する。
        return DateDisplay(calendar="western", text=f"{date.format_ja()}{suffix}")
    return DateDisplay(calendar="wareki", text=f"{wareki_text}{suffix}")


def _wareki_text(date: GDate) -> str | None:
    if date.kind != "dateval" or date.year is None:
        return None

    if is_pre_gregorian_adoption(date.year, date.month, date.day):
        # ADR-03: 明治 6 年 (1873) 以前は月日を確定表示しない。
        try:
            year_text = format_wareki_year(date.year)
        except ValueError:
            return None
    else:
        try:
            year_text = format_wareki_year(date.year, date.month, date.day)
        except ValueError:
            return None
        if date.month is not None:
            year_text += f"{kanji_number(date.month)}月"
            if date.day is not None:
                year_text += f"{kanji_number(date.day)}日"

    return year_text + _MODIFIER_SUFFIX.get(date.modifier or "", "")
