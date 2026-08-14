from __future__ import annotations

import gzip
import io
import tarfile
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def minimal_family_xml_bytes() -> bytes:
    """合成 Gramps XML フィクスチャの生バイト列。

    実データに依存せず、養子・再婚・旧姓・カナ・続柄・欠損日付の各パターンを
    含む最小家系 (tests/fixtures/minimal_family.gramps.xml) を返す。
    """
    return (FIXTURES_DIR / "minimal_family.gramps.xml").read_bytes()


# tests/fixtures/minimal_family.gramps.xml の object O0001 (_o0001) が参照する
# "GrampsMedia/I0004.jpg" のダミー内容。実画像である必要はない (バイト列の
# 往復のみをテストする)。
DUMMY_PHOTO_BYTES = b"\xff\xd8\xff\xe0 dummy jpeg bytes for testing \xff\xd9"


@pytest.fixture
def minimal_family_gpkg_bytes(minimal_family_xml_bytes: bytes) -> bytes:
    """minimal_family_xml_bytes を実際の .gpkg 形式 (tar.gz + 二重gzip) に包んだもの。

    GrampsDatabase.load() (API アップロード等、パス/ファイル入力を前提とする
    経路) のテストに使う。GPKG_FORMAT_NOTES.md の物理フォーマットに従う。
    `_o0001` (山田三郎の写真) に対応する `GrampsMedia/I0004.jpg` もダミー内容で
    同梱し、メディア取得の成功パスもテストできるようにする。
    """
    inner_gz = io.BytesIO()
    with gzip.GzipFile(fileobj=inner_gz, mode="wb") as gz:
        gz.write(minimal_family_xml_bytes)
    inner_gz_bytes = inner_gz.getvalue()

    outer = io.BytesIO()
    with tarfile.open(fileobj=outer, mode="w:gz") as tar:
        data_info = tarfile.TarInfo(name="data.gramps")
        data_info.size = len(inner_gz_bytes)
        tar.addfile(data_info, io.BytesIO(inner_gz_bytes))

        photo_info = tarfile.TarInfo(name="GrampsMedia/I0004.jpg")
        photo_info.size = len(DUMMY_PHOTO_BYTES)
        tar.addfile(photo_info, io.BytesIO(DUMMY_PHOTO_BYTES))
    return outer.getvalue()
