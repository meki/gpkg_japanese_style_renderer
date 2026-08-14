from __future__ import annotations

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
