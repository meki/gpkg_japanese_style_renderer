from __future__ import annotations

import pytest

from gpkg_jsr.format.wareki import format_wareki_year, is_pre_gregorian_adoption


class TestEdoPeriodEras:
    """江戸期の元号を慶長から令和まで連続して扱う。"""

    @pytest.mark.parametrize(
        ("year", "expected"),
        [
            (1596, "慶長元年"),
            (1615, "元和元年"),
            (1624, "寛永元年"),
            (1644, "正保元年"),
            (1648, "慶安元年"),
            (1652, "承応元年"),
            (1655, "明暦元年"),
            (1658, "万治元年"),
            (1661, "寛文元年"),
            (1673, "延宝元年"),
            (1681, "天和元年"),
            (1684, "貞享元年"),
            (1688, "元禄元年"),
            (1704, "宝永元年"),
            (1711, "正徳元年"),
            (1716, "享保元年"),
            (1736, "元文元年"),
            (1741, "寛保元年"),
            (1744, "延享元年"),
            (1748, "寛延元年"),
            (1751, "宝暦元年"),
            (1764, "明和元年"),
            (1772, "安永元年"),
            (1781, "天明元年"),
            (1789, "寛政元年"),
            (1801, "享和元年"),
            (1804, "文化元年"),
            (1818, "文政元年"),
            (1830, "天保元年"),
        ],
    )
    def test_era_start_years(self, year: int, expected: str) -> None:
        assert format_wareki_year(year) == expected

    def test_three_hundred_years_ago_is_supported(self) -> None:
        assert format_wareki_year(1726) == "享保十一年"

    def test_tenpo_start(self) -> None:
        assert format_wareki_year(1830) == "天保元年"

    def test_tenpo_1833(self) -> None:
        assert format_wareki_year(1833) == "天保四年"

    def test_tenpo_1840(self) -> None:
        assert format_wareki_year(1840) == "天保十一年"

    def test_bunkyu_1863(self) -> None:
        assert format_wareki_year(1863) == "文久三年"

    def test_genji_1864_boundary_resolves_to_new_era(self) -> None:
        # 文久・元治の境界は年単位の精度で扱うため (SP-04-01)、常に一意に決まる。
        assert format_wareki_year(1864) == "元治元年"

    def test_keio_1867(self) -> None:
        assert format_wareki_year(1867) == "慶応三年"

    def test_out_of_table_range_raises(self) -> None:
        with pytest.raises(ValueError):
            format_wareki_year(1595)


class TestModernEraBoundaries:
    """大正以降は日単位の精度を持つため、月日が不明な境界年は複数候補を返す (SP-04-02)。"""

    def test_meiji_taisho_boundary_year_is_ambiguous(self) -> None:
        assert format_wareki_year(1912) == "明治四十五年/大正元年"

    def test_meiji_taisho_boundary_disambiguated_by_date(self) -> None:
        assert format_wareki_year(1912, 7, 29) == "明治四十五年"
        assert format_wareki_year(1912, 7, 30) == "大正元年"

    def test_taisho_showa_boundary_year_is_ambiguous(self) -> None:
        assert format_wareki_year(1926) == "大正十五年/昭和元年"

    def test_taisho_showa_boundary_disambiguated_by_date(self) -> None:
        assert format_wareki_year(1926, 12, 24) == "大正十五年"
        assert format_wareki_year(1926, 12, 25) == "昭和元年"

    def test_showa_heisei_boundary_year_is_ambiguous(self) -> None:
        assert format_wareki_year(1989) == "昭和六十四年/平成元年"

    def test_showa_heisei_boundary_disambiguated_by_date(self) -> None:
        assert format_wareki_year(1989, 1, 7) == "昭和六十四年"
        assert format_wareki_year(1989, 1, 8) == "平成元年"

    def test_heisei_reiwa_boundary_year_is_ambiguous(self) -> None:
        assert format_wareki_year(2019) == "平成三十一年/令和元年"

    def test_heisei_reiwa_boundary_disambiguated_by_date(self) -> None:
        assert format_wareki_year(2019, 4, 30) == "平成三十一年"
        assert format_wareki_year(2019, 5, 1) == "令和元年"

    def test_non_boundary_year_is_unambiguous(self) -> None:
        assert format_wareki_year(1990) == "平成二年"
        assert format_wareki_year(1913) == "大正二年"

    def test_ongoing_era_has_no_upper_bound(self) -> None:
        assert format_wareki_year(2030) == "令和十二年"


class TestPreGregorianAdoption:
    """明治 6 年 (1873) の太陽暦採用日より前かどうかの判定 (SP-04-04, ADR-03)。"""

    @pytest.mark.parametrize("year", [1833, 1840, 1863, 1864, 1872])
    def test_years_before_1873_are_pre_adoption(self, year: int) -> None:
        assert is_pre_gregorian_adoption(year, None, None) is True

    @pytest.mark.parametrize("year", [1873, 1900, 2026])
    def test_years_from_1873_onward_are_not_pre_adoption(self, year: int) -> None:
        assert is_pre_gregorian_adoption(year, None, None) is False

    def test_1873_exact_boundary_with_full_date(self) -> None:
        assert is_pre_gregorian_adoption(1873, 1, 1) is False
        assert is_pre_gregorian_adoption(1872, 12, 31) is True

    def test_1873_without_month_day_is_not_flagged_pre_adoption(self) -> None:
        # 年しか分からない場合、月日不明のまま「採用前」と断定しない (安全側)。
        assert is_pre_gregorian_adoption(1873, None, None) is False
