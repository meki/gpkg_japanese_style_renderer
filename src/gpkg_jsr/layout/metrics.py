"""縦書きノードの寸法推定 (ADR-01)。

フォントの実際のグリフ幅を実測せず、文字数ベースの近似でノードの占有幅・高さを
見積もる。抽象座標系における 1 単位は全角文字 1 文字分の字送り (1em 相当) と
みなす。実際のグリフ幅とは厳密には一致せず、ノードの重なりが生じうるが、
それは Phase 6 のレイアウト品質改善で吸収する方針とする (ADR-01 参照)。
"""
from __future__ import annotations

from gpkg_jsr.layout.types import DisplayOptions, NodeSize
from gpkg_jsr.model.view import PersonView

CHAR_UNIT = 1.0
MAIN_COLUMN_WIDTH = 1.0
RUBY_COLUMN_WIDTH = 0.5
LABEL_COLUMN_WIDTH = 0.6
DATE_COLUMN_WIDTH = 0.6
PADDING = 0.4
PHOTO_WIDTH = 2.4
PHOTO_HEIGHT = 3.0
MIN_WIDTH = 1.5
MIN_HEIGHT = 2.0


def estimate_node_size(view: PersonView, options: DisplayOptions) -> NodeSize:
    """PersonView と表示トグルから、抽象座標系でのノード寸法を見積もる。"""
    name_chars = len(view.surname) + len(view.given_name)
    if options.show_former_surname and view.former_surname:
        name_chars += len(view.former_surname)

    side_columns = 0
    if options.show_ruby and (view.surname_kana or view.given_name_kana):
        side_columns += 1
    if options.show_birth_order and view.birth_order_label:
        side_columns += 1

    dates_chars = 0
    if options.show_dates:
        if view.birth_date_display is not None:
            dates_chars += len(view.birth_date_display.text)
        if view.death_date_display is not None:
            dates_chars += len(view.death_date_display.text)
        if dates_chars:
            side_columns += 1

    text_height = max(name_chars, dates_chars) * CHAR_UNIT
    text_width = MAIN_COLUMN_WIDTH + side_columns * max(
        RUBY_COLUMN_WIDTH, LABEL_COLUMN_WIDTH, DATE_COLUMN_WIDTH
    )

    has_photo = options.show_photos and view.has_photo
    height = text_height + (PHOTO_HEIGHT if has_photo else 0.0) + PADDING * 2
    width = max(text_width, PHOTO_WIDTH if has_photo else 0.0) + PADDING * 2

    return NodeSize(width=max(width, MIN_WIDTH), height=max(height, MIN_HEIGHT))
