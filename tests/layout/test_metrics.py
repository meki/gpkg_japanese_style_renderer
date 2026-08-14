from __future__ import annotations

from gpkg_jsr.layout.metrics import estimate_node_size
from gpkg_jsr.layout.types import DisplayOptions
from gpkg_jsr.model.view import DateDisplay, PersonView


def _view(**overrides: object) -> PersonView:
    base: dict[str, object] = dict(
        surname="山田",
        given_name="太郎",
        is_spouse_in=False,
        is_deceased=False,
        has_photo=False,
        gender="M",
    )
    base.update(overrides)
    return PersonView(**base)  # type: ignore[arg-type]


def test_longer_name_yields_taller_node() -> None:
    short = estimate_node_size(_view(given_name="太"), DisplayOptions())
    long = estimate_node_size(_view(given_name="太郎兵衛長政"), DisplayOptions())
    assert long.height > short.height


def test_ruby_toggle_widens_node_when_kana_present() -> None:
    view = _view(surname_kana="やまだ", given_name_kana="たろう")
    with_ruby = estimate_node_size(view, DisplayOptions(show_ruby=True))
    without_ruby = estimate_node_size(view, DisplayOptions(show_ruby=False))
    assert with_ruby.width > without_ruby.width


def test_ruby_toggle_has_no_effect_without_kana() -> None:
    view = _view()  # kana 未設定
    with_ruby = estimate_node_size(view, DisplayOptions(show_ruby=True))
    without_ruby = estimate_node_size(view, DisplayOptions(show_ruby=False))
    assert with_ruby.width == without_ruby.width


def test_photo_toggle_grows_node() -> None:
    view = _view(has_photo=True)
    with_photo = estimate_node_size(view, DisplayOptions(show_photos=True))
    without_photo = estimate_node_size(view, DisplayOptions(show_photos=False))
    assert with_photo.height > without_photo.height
    assert with_photo.width >= without_photo.width


def test_dates_toggle_affects_total_width_but_not_frame() -> None:
    view = _view(
        birth_date_display=DateDisplay(calendar="wareki", text="明治二十七年八月十二日生")
    )
    with_dates = estimate_node_size(view, DisplayOptions(show_dates=True))
    without_dates = estimate_node_size(view, DisplayOptions(show_dates=False))
    assert with_dates.width > without_dates.width
    assert with_dates.date_column_width > 0
    assert without_dates.date_column_width == 0


def test_long_dates_do_not_inflate_the_frame() -> None:
    """罫線ボックス (frame) の高さ・幅は生没年の長さに左右されない。

    和暦の生没年表記は "明治二十七年八月十二日生" のように長くなりがちで、
    これを frame の高さ計算に含めると短い名前の人物のノードまで不必要に
    縦長になっていた (実データでのレイアウト確認で発覚した回帰)。
    """
    short_name = _view(given_name="太")
    long_dates = _view(
        given_name="太",
        birth_date_display=DateDisplay(calendar="wareki", text="明治二十七年八月十二日生"),
        death_date_display=DateDisplay(calendar="wareki", text="昭和六十三年十二月三十一日没"),
    )
    without_dates = estimate_node_size(short_name, DisplayOptions())
    with_long_dates = estimate_node_size(long_dates, DisplayOptions())
    assert with_long_dates.height == without_dates.height
    assert with_long_dates.frame_width == without_dates.frame_width
    # 生没年自体の縦の長さは date_column_height として別途持ち、行間確保に使う
    assert with_long_dates.date_column_height > with_long_dates.height


def test_minimum_size_is_enforced_for_empty_view() -> None:
    view = _view(surname="", given_name="")
    size = estimate_node_size(view, DisplayOptions())
    assert size.width > 0
    assert size.height > 0
    assert size.frame_width > 0
