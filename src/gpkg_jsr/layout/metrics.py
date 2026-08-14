"""縦書きノードの寸法推定 (ADR-01)。

フォントの実際のグリフ幅を実測せず、文字数ベースの近似でノードの占有幅・高さを
見積もる。抽象座標系における 1 単位は全角文字 1 文字分の字送り (1em 相当) と
みなす。実際のグリフ幅とは厳密には一致せず、ノードの重なりが生じうるが、
それは Phase 6 のレイアウト品質改善で吸収する方針とする (ADR-01 参照)。

生没年 (dates) は罫線で囲むノード本体 (frame) の高さには含めない。和暦の
生没年表記は "明治二十七年八月十二日生" のように長くなりがちで、これを
frame の高さに含めると名前が短い人物のノードまで不必要に縦長になる
(実データで確認されたレイアウト崩れ)。生没年は `date_column_width` /
`date_column_height` として frame とは別に見積もり、描画層 (VerticalNode.tsx)
が frame の外側 (画面表示では右隣) に独立した列として配置する。
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

    text_height = name_chars * CHAR_UNIT
    text_width = MAIN_COLUMN_WIDTH + side_columns * max(RUBY_COLUMN_WIDTH, LABEL_COLUMN_WIDTH)

    has_photo = options.show_photos and view.has_photo
    frame_height = max(text_height + (PHOTO_HEIGHT if has_photo else 0.0) + PADDING * 2, MIN_HEIGHT)
    frame_width = max(
        max(text_width, PHOTO_WIDTH if has_photo else 0.0) + PADDING * 2, MIN_WIDTH
    )

    date_column_width = 0.0
    date_column_height = 0.0
    if dates_chars > 0:
        date_column_width = DATE_COLUMN_WIDTH + PADDING
        date_column_height = dates_chars * CHAR_UNIT + PADDING * 2

    return NodeSize(
        width=frame_width + date_column_width,
        height=frame_height,
        frame_width=frame_width,
        date_column_width=date_column_width,
        date_column_height=date_column_height,
    )
