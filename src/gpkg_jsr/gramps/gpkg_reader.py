"""
Gramps .gpkg (Gramps Package) 読み取り用モジュール。

.gpkg = tar.gz アーカイブ。中の "data.gramps" は *さらに* gzip 圧縮された
Gramps XML (1.7.x)、それ以外のエントリはメディアファイル(画像等)。

詳しい仕様は同ディレクトリの GPKG_FORMAT_NOTES.md を参照。

使い方:

    from gpkg_reader import GrampsDatabase

    db = GrampsDatabase.load("山田家系図.gpkg")

    for person in db.people.values():
        print(person.display_name(), db.birth_date(person), db.death_date(person))

    root = db.roots()[0]                 # childof を持たない = 最古の祖先
    for child in db.children(root):
        print(child.display_name())

    photo = db.media_bytes(db.objects[person.objrefs[0]])   # bytes (JPEG等)
"""
from __future__ import annotations

import gzip
import re
import tarfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

# ----------------------------------------------------------------------
# 日付 (dateval / daterange / datespan / datestr) のパース
# ----------------------------------------------------------------------

_DATEVAL_RE = re.compile(r"^(\d{4}|\?{4})(?:-(\d{2}|\?{2}))?(?:-(\d{2}))?$")


def _parse_ymd(val: str) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """"1982-04-08" / "1982-04" / "1982" / "????-04-08" 等を (year, month, day) に変換。
    どの部分も不明なら None。パース不能なら (None, None, None)。"""
    m = _DATEVAL_RE.match(val)
    if not m:
        return None, None, None
    y, mo, d = m.groups()
    year = None if y in (None, "????") else int(y)
    month = None if mo in (None, "??") else int(mo)
    day = None if d is None else int(d)
    return year, month, day


@dataclass
class GDate:
    """Gramps の日付表現 (dateval / daterange / datespan / datestr) をまとめて扱うクラス。"""

    kind: str  # "dateval" | "daterange" | "datespan" | "datestr"
    year: Optional[int] = None
    month: Optional[int] = None
    day: Optional[int] = None
    modifier: Optional[str] = None  # "before" | "after" | "about"  (dateval のみ)
    quality: Optional[str] = None  # "estimated" | "calculated"
    start: Optional[tuple] = None  # daterange/datespan の開始 (y, m, d)
    stop: Optional[tuple] = None  # daterange/datespan の終了 (y, m, d)
    text: Optional[str] = None  # datestr の生テキスト、またはフォールバック表示
    raw: Optional[str] = None  # 元の val 文字列

    @property
    def year_known(self) -> bool:
        return self.year is not None

    def format_ja(self) -> str:
        """日本語の家系図表示向けにざっくり整形する (例: "1982年4月8日", "1982年頃", "1809年～1885年")。
        情報が欠けている場合は分かる範囲だけを出す。"""
        if self.kind == "datestr":
            return self.text or ""

        def ymd(y, mo, d) -> str:
            if y is None:
                return "生年月日不詳" if mo is None and d is None else "?年" + (
                    f"{mo}月" if mo else ""
                ) + (f"{d}日" if d else "")
            s = f"{y}年"
            if mo:
                s += f"{mo}月"
            if d:
                s += f"{d}日"
            return s

        if self.kind in ("daterange", "datespan"):
            sep = "〜" if self.kind == "daterange" else "頃〜"
            start_s = ymd(*self.start) if self.start else "?"
            stop_s = ymd(*self.stop) if self.stop else "?"
            return f"{start_s}{sep}{stop_s}"

        s = ymd(self.year, self.month, self.day)
        if self.modifier == "about":
            s += "頃"
        elif self.modifier == "before":
            s = s + "以前"
        elif self.modifier == "after":
            s = s + "以後"
        return s

    def __str__(self) -> str:
        return self.format_ja()


def parse_date(parent: ET.Element) -> Optional[GDate]:
    """event/name/object/... 等の親要素の直下から dateval|daterange|datespan|datestr を探してパースする。
    見つからなければ None。"""
    for child in parent:
        tag = _local(child.tag)
        if tag == "dateval":
            val = child.get("val", "")
            y, mo, d = _parse_ymd(val)
            return GDate(
                kind="dateval",
                year=y,
                month=mo,
                day=d,
                modifier=child.get("type"),
                quality=child.get("quality"),
                raw=val,
            )
        if tag in ("daterange", "datespan"):
            start = _parse_ymd(child.get("start", ""))
            stop = _parse_ymd(child.get("stop", ""))
            return GDate(
                kind=tag,
                start=start,
                stop=stop,
                quality=child.get("quality"),
                raw=f'{child.get("start")}..{child.get("stop")}',
            )
        if tag == "datestr":
            val = child.get("val", "")
            return GDate(kind="datestr", text=val, raw=val)
    return None


# ----------------------------------------------------------------------
# XML namespace ヘルパ (Gramps XML のバージョン差 1.7.1 / 1.7.2 等を吸収する)
# ----------------------------------------------------------------------


def _local(tag: str) -> str:
    """"{http://gramps-project.org/xml/1.7.2/}person" -> "person" """
    return tag.rsplit("}", 1)[-1]


def _children(elem: ET.Element, name: str):
    return [c for c in elem if _local(c.tag) == name]


def _child(elem: ET.Element, name: str) -> Optional[ET.Element]:
    for c in elem:
        if _local(c.tag) == name:
            return c
    return None


def _text(elem: Optional[ET.Element]) -> Optional[str]:
    return elem.text if elem is not None else None


# ----------------------------------------------------------------------
# データモデル
# ----------------------------------------------------------------------


@dataclass
class Name:
    first: str = ""
    surname: str = ""
    prefix: str = ""
    suffix: str = ""
    nick: str = ""
    type: str = ""  # "Birth Name" | "Married Name" | "Also Known As" | ...
    is_alt: bool = False

    def full(self) -> str:
        """日本式の「姓 名」表記。"""
        parts = [p for p in (self.surname, self.first) if p]
        return " ".join(parts)


@dataclass
class Person:
    handle: str
    id: str
    gender: str = "U"  # "M" | "F" | "U" | "X"
    names: list = field(default_factory=list)  # list[Name] (先頭が主名)
    eventrefs: list = field(default_factory=list)  # list[(handle, role)]
    objrefs: list = field(default_factory=list)  # list[handle]
    attributes: list = field(default_factory=list)  # list[(type, value)]
    childof: list = field(default_factory=list)  # list[family handle] (実親/養親)
    parentin: list = field(default_factory=list)  # list[family handle] (配偶者関係)
    noterefs: list = field(default_factory=list)  # list[handle]

    @property
    def primary_name(self) -> Name:
        return self.names[0] if self.names else Name()

    @property
    def alt_names(self) -> list:
        return [n for n in self.names if n.is_alt] or self.names[1:]

    def display_name(self) -> str:
        return self.primary_name.full() or "(名前不明)"

    def is_male(self) -> bool:
        return self.gender == "M"

    def is_female(self) -> bool:
        return self.gender == "F"

    def get_attribute(self, type_: str) -> Optional[str]:
        for t, v in self.attributes:
            if t == type_:
                return v
        return None


@dataclass
class ChildRef:
    person_handle: str
    frel: str = "Birth"  # None|Birth|Adopted|Stepchild|Sponsored|Foster|Other|Unknown
    mrel: str = "Birth"


@dataclass
class Family:
    handle: str
    id: str
    rel_type: Optional[str] = None  # "Married" | "Unmarried" | "Civil Union" | ...
    father_handle: Optional[str] = None
    mother_handle: Optional[str] = None
    children: list = field(default_factory=list)  # list[ChildRef]
    eventrefs: list = field(default_factory=list)  # list[(handle, role)]


@dataclass
class Event:
    handle: str
    id: str
    type: str = ""  # "Birth" | "Death" | "Marriage" | ...
    date: Optional[GDate] = None
    place_handle: Optional[str] = None
    description: str = ""


@dataclass
class MediaObject:
    handle: str
    id: str
    src: str = ""  # アーカイブ内相対パス (= tar のメンバ名)
    mime: str = ""
    checksum: str = ""
    description: str = ""


@dataclass
class Note:
    handle: str
    id: str
    type: str = ""
    text: str = ""


@dataclass
class Place:
    handle: str
    id: str
    title: str = ""


# ----------------------------------------------------------------------
# GrampsDatabase 本体
# ----------------------------------------------------------------------


class GrampsDatabase:
    """1つの .gpkg (または直接 data.gramps の XML bytes) を読み込んでメモリ上に保持する。"""

    def __init__(self) -> None:
        self.people: dict[str, Person] = {}
        self.families: dict[str, Family] = {}
        self.events: dict[str, Event] = {}
        self.objects: dict[str, MediaObject] = {}
        self.notes: dict[str, Note] = {}
        self.places: dict[str, Place] = {}
        self._media_files: dict[str, bytes] = {}  # src(アーカイブ内パス) -> bytes

    # ---- 読み込み ----------------------------------------------------

    @classmethod
    def load(cls, gpkg_path: str | Path) -> "GrampsDatabase":
        """.gpkg ファイルから読み込む(tar.gz -> data.gramps を二重gzip解凍 -> XMLパース)。
        メディアファイルはすべて一度にメモリへ展開する。"""
        db = cls()
        with tarfile.open(gpkg_path, "r:gz") as tar:
            data_member = tar.extractfile("data.gramps")
            if data_member is None:
                raise ValueError("data.gramps が見つかりません(.gpkg として不正な可能性)")
            xml_bytes = gzip.decompress(data_member.read())

            for member in tar.getmembers():
                if member.name == "data.gramps" or not member.isfile():
                    continue
                f = tar.extractfile(member)
                if f is not None:
                    db._media_files[member.name] = f.read()

        db._parse_xml(xml_bytes)
        return db

    @classmethod
    def load_xml_bytes(cls, xml_bytes: bytes) -> "GrampsDatabase":
        """data.gramps (gzip解凍済みXML) の bytes を直接読み込む場合。メディアは扱わない。"""
        db = cls()
        db._parse_xml(xml_bytes)
        return db

    def _parse_xml(self, xml_bytes: bytes) -> None:
        root = ET.fromstring(xml_bytes)

        places_elem = _child(root, "places")
        if places_elem is not None:
            for pl in _children(places_elem, "placeobj"):
                ptitle = _text(_child(pl, "ptitle")) or ""
                self.places[pl.get("handle")] = Place(
                    handle=pl.get("handle"), id=pl.get("id", ""), title=ptitle
                )

        events_elem = _child(root, "events")
        if events_elem is not None:
            for ev in _children(events_elem, "event"):
                place = _child(ev, "place")
                self.events[ev.get("handle")] = Event(
                    handle=ev.get("handle"),
                    id=ev.get("id", ""),
                    type=_text(_child(ev, "type")) or "",
                    date=parse_date(ev),
                    place_handle=place.get("hlink") if place is not None else None,
                    description=_text(_child(ev, "description")) or "",
                )

        objects_elem = _child(root, "objects")
        if objects_elem is not None:
            for obj in _children(objects_elem, "object"):
                file_el = _child(obj, "file")
                self.objects[obj.get("handle")] = MediaObject(
                    handle=obj.get("handle"),
                    id=obj.get("id", ""),
                    src=file_el.get("src", "") if file_el is not None else "",
                    mime=file_el.get("mime", "") if file_el is not None else "",
                    checksum=file_el.get("checksum", "") if file_el is not None else "",
                    description=file_el.get("description", "") if file_el is not None else "",
                )

        notes_elem = _child(root, "notes")
        if notes_elem is not None:
            for nt in _children(notes_elem, "note"):
                self.notes[nt.get("handle")] = Note(
                    handle=nt.get("handle"),
                    id=nt.get("id", ""),
                    type=nt.get("type", ""),
                    text=_text(_child(nt, "text")) or "",
                )

        people_elem = _child(root, "people")
        if people_elem is not None:
            for p in _children(people_elem, "person"):
                names = []
                for n in _children(p, "name"):
                    first = _text(_child(n, "first")) or ""
                    surnames = [_text(s) or "" for s in _children(n, "surname")]
                    names.append(
                        Name(
                            first=first,
                            surname=" ".join(s for s in surnames if s),
                            suffix=_text(_child(n, "suffix")) or "",
                            nick=_text(_child(n, "nick")) or "",
                            type=n.get("type", ""),
                            is_alt=n.get("alt") == "1",
                        )
                    )
                eventrefs = [
                    (er.get("hlink"), er.get("role", "")) for er in _children(p, "eventref")
                ]
                objrefs = [orf.get("hlink") for orf in _children(p, "objref")]
                attrs = [
                    (a.get("type", ""), a.get("value", "")) for a in _children(p, "attribute")
                ]
                childof = [c.get("hlink") for c in _children(p, "childof")]
                parentin = [c.get("hlink") for c in _children(p, "parentin")]
                noterefs = [nr.get("hlink") for nr in _children(p, "noteref")]

                self.people[p.get("handle")] = Person(
                    handle=p.get("handle"),
                    id=p.get("id", ""),
                    gender=_text(_child(p, "gender")) or "U",
                    names=names,
                    eventrefs=eventrefs,
                    objrefs=objrefs,
                    attributes=attrs,
                    childof=childof,
                    parentin=parentin,
                    noterefs=noterefs,
                )

        families_elem = _child(root, "families")
        if families_elem is not None:
            for fam in _children(families_elem, "family"):
                rel = _child(fam, "rel")
                father = _child(fam, "father")
                mother = _child(fam, "mother")
                children = []
                for cr in _children(fam, "childref"):
                    children.append(
                        ChildRef(
                            person_handle=cr.get("hlink"),
                            frel=cr.get("frel", "Birth"),
                            mrel=cr.get("mrel", "Birth"),
                        )
                    )
                eventrefs = [
                    (er.get("hlink"), er.get("role", "")) for er in _children(fam, "eventref")
                ]
                self.families[fam.get("handle")] = Family(
                    handle=fam.get("handle"),
                    id=fam.get("id", ""),
                    rel_type=rel.get("type") if rel is not None else None,
                    father_handle=father.get("hlink") if father is not None else None,
                    mother_handle=mother.get("hlink") if mother is not None else None,
                    children=children,
                    eventrefs=eventrefs,
                )

    # ---- 参照解決・クエリ ---------------------------------------------

    def get_person(self, handle: Optional[str]) -> Optional[Person]:
        return self.people.get(handle) if handle else None

    def get_family(self, handle: Optional[str]) -> Optional[Family]:
        return self.families.get(handle) if handle else None

    def _person_event(self, person: Person, event_type: str) -> Optional[Event]:
        for handle, _role in person.eventrefs:
            ev = self.events.get(handle)
            if ev is not None and ev.type == event_type:
                return ev
        return None

    def birth_date(self, person: Person) -> Optional[GDate]:
        ev = self._person_event(person, "Birth")
        return ev.date if ev else None

    def death_date(self, person: Person) -> Optional[GDate]:
        ev = self._person_event(person, "Death")
        return ev.date if ev else None

    def is_deceased(self, person: Person) -> bool:
        return self._person_event(person, "Death") is not None

    def spouses(self, person: Person) -> list:
        """配偶者一覧 (再婚などで複数ありうる)。"""
        result = []
        for fh in person.parentin:
            fam = self.families.get(fh)
            if fam is None:
                continue
            other = fam.father_handle if fam.mother_handle == person.handle else fam.mother_handle
            other_p = self.get_person(other)
            if other_p is not None:
                result.append(other_p)
        return result

    def children(self, person: Person) -> list:
        """person が親として関わる全 family の子を、生年順(不明は末尾)でまとめて返す。"""
        result = []
        for fh in person.parentin:
            fam = self.families.get(fh)
            if fam is None:
                continue
            for cr in fam.children:
                child = self.get_person(cr.person_handle)
                if child is not None:
                    result.append(child)

        def sort_key(pp: Person):
            d = self.birth_date(pp)
            return (0, (d.year or 9999, d.month or 99, d.day or 99)) if d else (1, (9999, 99, 99))

        result.sort(key=sort_key)
        return result

    def children_with_relation(self, family: Family) -> list:
        """family.children を (Person, frel, mrel) のリストで返す(実子/養子の区別に使う)。"""
        result = []
        for cr in family.children:
            child = self.get_person(cr.person_handle)
            if child is not None:
                result.append((child, cr.frel, cr.mrel))
        return result

    def parents(self, person: Person) -> list:
        """person の親 family (複数ありうる: 実親 + 養親) を [(father, mother, frel, mrel), ...] で返す。
        frel/mrel はその family における person 自身の childref から取る。"""
        result = []
        for fh in person.childof:
            fam = self.families.get(fh)
            if fam is None:
                continue
            frel = mrel = "Birth"
            for cr in fam.children:
                if cr.person_handle == person.handle:
                    frel, mrel = cr.frel, cr.mrel
                    break
            result.append(
                (self.get_person(fam.father_handle), self.get_person(fam.mother_handle), frel, mrel)
            )
        return result

    def notes_for(self, obj) -> list:
        """person/family/event 等の noterefs からテキスト一覧を返す。"""
        texts = []
        for nh in getattr(obj, "noterefs", []):
            note = self.notes.get(nh)
            if note is not None:
                texts.append(note.text)
        return texts

    def roots(self) -> list:
        """childof を一切持たない人物(= 家系図上、これ以上遡れない最古の代)の一覧。"""
        return [p for p in self.people.values() if not p.childof]

    def media_bytes(self, media: MediaObject) -> Optional[bytes]:
        """MediaObject に対応する実データ (bytes) を返す。GrampsDatabase.load() 経由で
        読み込んだ場合のみ利用可能 (load_xml_bytes() ではメディアは読み込まれない)。"""
        return self._media_files.get(media.src)

    def photo_bytes(self, person: Person) -> Optional[bytes]:
        """person の最初のメディア(通常は写真)を bytes で返す。無ければ None。"""
        for oh in person.objrefs:
            media = self.objects.get(oh)
            if media is not None:
                data = self.media_bytes(media)
                if data is not None:
                    return data
        return None


# ----------------------------------------------------------------------
# 動作確認用 (直接実行された場合のみ)
# ----------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: python gpkg_reader.py <file.gpkg>")
        raise SystemExit(1)

    db = GrampsDatabase.load(sys.argv[1])
    print(f"people={len(db.people)} families={len(db.families)} "
          f"events={len(db.events)} objects={len(db.objects)} notes={len(db.notes)}")

    for root_person in db.roots()[:5]:
        b = db.birth_date(root_person)
        d = db.death_date(root_person)
        print(f"- {root_person.display_name()}  生:{b or '?'}  没:{d or '?'}"
              f"  子={len(db.children(root_person))}人")
