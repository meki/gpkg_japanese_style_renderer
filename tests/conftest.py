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


@pytest.fixture
def minimal_family_gpkg_bytes(minimal_family_xml_bytes: bytes) -> bytes:
    """minimal_family_xml_bytes を実際の .gpkg 形式 (tar.gz + 二重gzip) に包んだもの。

    GrampsDatabase.load() (API アップロード等、パス/ファイル入力を前提とする
    経路) のテストに使う。GPKG_FORMAT_NOTES.md の物理フォーマットに従う。
    """
    inner_gz = io.BytesIO()
    with gzip.GzipFile(fileobj=inner_gz, mode="wb") as gz:
        gz.write(minimal_family_xml_bytes)
    inner_gz_bytes = inner_gz.getvalue()

    outer = io.BytesIO()
    with tarfile.open(fileobj=outer, mode="w:gz") as tar:
        info = tarfile.TarInfo(name="data.gramps")
        info.size = len(inner_gz_bytes)
        tar.addfile(info, io.BytesIO(inner_gz_bytes))
    return outer.getvalue()
