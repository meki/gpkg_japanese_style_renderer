"""縦書きノードの寸法推定 (ADR-01)。

フォントの実際のグリフ幅を実測せず、文字数ベースの近似でノードの占有幅・高さを
見積もる。実際のグリフ幅とは厳密には一致せず、ノードの重なりが生じうるが、
それは Phase 6 のレイアウト品質改善で吸収する方針とする (ADR-01 参照)。

抽象座標系の 1 単位は `web/src/canvas/layoutConstants.ts` の `UNIT_PX` (32px) に
対応する (下記 `_UNIT_PX` として同じ値を持つ)。以下の `_..._PX` 定数は、
`VerticalNode.css` と同じ CSS (font-size / line-height / gap / padding / border)
を独立した静的 HTML に再現し、**制約なしで自然にレンダリングさせた状態**で
`getBoundingClientRect()` により実測した px 値である (2 文字・6 文字など複数の
文字数パターンで線形性を確認済み)。アプリ内の実ノードから直接測ると、
`.vertical-node` 自体に明示的な width/height を指定しているため、内容が
収まらない場合に縦書きテキストが折り返して余分な列を生成してしまい
(その状態を「正しいサイズ」だと誤認すると frame が常に足りなくなる)、
誤った値を実測してしまう。必ず制約なしの自然なサイズを基準にすること。

文字数だけを見て単純に 1 文字 = 1 単位のような粗い近似にすると、実際に
描画される文字よりも frame が数倍大きくなり、無駄な余白として実データ確認で
指摘された。逆に、安全マージンを削りすぎると、名前の折り返し（縦書きで
文字が入りきらず余分な列ができてしまう不具合）が発生する（旧姓・続柄が
同時に付く人物で実際に発生した回帰）。以下の定数は実測値に対してわずかな
安全マージンを載せてあるが、フォント設定を変更した場合はこれらの定数も
実測し直すこと。

生没年 (dates) と顔写真は、罫線で囲むノード本体 (frame) の寸法には含めない。
和暦の生没年表記は "明治二十七年八月十二日生" のように長くなりがちで、これを
frame の寸法に含めると名前が短い人物のノードまで不必要に縦長になる
(実データで確認されたレイアウト崩れ)。生没年は `date_column_width` /
`date_column_height` として frame の外側 (画面表示では frame の右隣) に、顔写真は
`photo_height` として frame の外側 (画面表示では下) に、それぞれ独立した
領域として描画層 (VerticalNode.tsx) が配置する。
"""
from __future__ import annotations

from gpkg_jsr.layout.types import DisplayOptions, NodeSize
from gpkg_jsr.model.view import PersonView

_UNIT_PX = 32.0  # web/src/canvas/layoutConstants.ts の UNIT_PX と同じ値

# 姓・名 (font-size: 1em = 15px) 1 文字あたりの高さ。実測 15.0px/文字 (2文字・
# 6文字のいずれでも線形)。
_MAIN_CHAR_PX = 15.0
# .vertical-node__name の gap: 0.1em = 1.5px。姓-名間、(旧姓を表示する場合は)
# 旧姓-姓間にそれぞれ 1 回ずつ挟まる。
_NAME_GAP_PX = 1.5
# 旧姓 ("(鈴木)" のように括弧付きで表示、font-size: 0.6em) の表示文字 1 文字
# あたりの高さ。実測 6.14px/文字 (括弧2文字を含めた文字数で割った値) に安全
# マージンを載せている。
_FORMER_CHAR_PX = 6.5
# 続柄ラベル (font-size: 0.55em) 1 文字あたりの高さ。実測 8.25px/文字
# (= font-size そのもの)。
_LABEL_CHAR_PX = 8.6
# .vertical-node の gap: 0.2em = 3px。名前ブロックと続柄ラベルの間に挟まる。
_BLOCK_GAP_PX = 3.0
# .vertical-node の padding: 0.2em = 3px (片側)。
_PADDING_PX = 3.2
# .vertical-node の border: 1px (片側)。
_BORDER_PX = 1.0
# 名前 1 列の幅 (ルビ非表示時)。実測 17.25px に安全マージン。
_MAIN_COLUMN_WIDTH_PX = 19.0
# ルビ表示時に名前列へ追加される幅。実測 8.32px (25.57 - 17.25) に安全マージン。
_RUBY_EXTRA_WIDTH_PX = 9.5
# 続柄ラベル列の幅 (1列、文字数によらずほぼ一定)。実測 12.16px に安全マージン。
_LABEL_COLUMN_WIDTH_PX = 14.0
# サブピクセルの丸め・フォントレンダリングの微差だけで折り返しが起きないよう
# 明確に載せる追加の安全マージン (frame 全体に対して一律に加える)。
_HEIGHT_SAFETY_PX = 10.0
_WIDTH_SAFETY_PX = 6.0

MAIN_COLUMN_WIDTH = _MAIN_COLUMN_WIDTH_PX / _UNIT_PX
DATE_COLUMN_WIDTH = 0.6
# 顔写真の縦横比 (高さ/幅)。実測画像を使わないため固定比率で近似する。
PHOTO_ASPECT_RATIO = 1.25
# frame 下端と顔写真の間の隙間。
PHOTO_GAP = 0.15
MIN_WIDTH = 0.8
MIN_HEIGHT = 1.2


def estimate_node_size(view: PersonView, options: DisplayOptions) -> NodeSize:
    """PersonView と表示トグルから、抽象座標系でのノード寸法を見積もる。"""
    surname_given_chars = len(view.surname) + len(view.given_name)

    former_surname = view.former_surname if options.show_former_surname else None
    show_former = bool(former_surname)
    # "(" + 旧姓 + ")" の表示文字数
    former_display_chars = len(former_surname) + 2 if former_surname else 0

    show_ruby = bool(options.show_ruby and (view.surname_kana or view.given_name_kana))
    show_label = bool(options.show_birth_order and view.birth_order_label)

    # 名前ブロック (旧姓 + 姓ruby + 名ruby を縦に積む) の高さ。
    name_height_px = surname_given_chars * _MAIN_CHAR_PX + _NAME_GAP_PX  # 姓-名間の gap
    if show_former:
        name_height_px += former_display_chars * _FORMER_CHAR_PX + _NAME_GAP_PX

    # 名前ブロックの幅。ルビは姓・名と同じ列に注記として追加されるだけで
    # 別列にはならない (続柄ラベルとは異なり、名前ブロックの下に積まれない)。
    name_width_px = _MAIN_COLUMN_WIDTH_PX + (_RUBY_EXTRA_WIDTH_PX if show_ruby else 0.0)

    # 続柄ラベルは名前ブロックの下に別ブロックとして積まれる (横には並ばない)。
    label_height_px = 0.0
    label_width_px = 0.0
    if show_label:
        assert view.birth_order_label is not None
        label_height_px = len(view.birth_order_label) * _LABEL_CHAR_PX + _BLOCK_GAP_PX
        label_width_px = _LABEL_COLUMN_WIDTH_PX

    content_height_px = name_height_px + label_height_px
    content_width_px = max(name_width_px, label_width_px)

    # 実測値どおりの値をそのまま frame の寸法にすると、ブラウザのサブピクセル
    # 丸め・フォントレンダリングの誤差だけで「1px 足りず折り返される」際どい
    # 状態になる (実際に発生した回帰: 実測値と丸々同じ余白では名前が二列に
    # 折り返された)。安全のため明確な余裕を追加で載せる。
    frame_height = max(
        (content_height_px + _PADDING_PX * 2 + _BORDER_PX * 2 + _HEIGHT_SAFETY_PX) / _UNIT_PX,
        MIN_HEIGHT,
    )
    frame_width = max(
        (content_width_px + _PADDING_PX * 2 + _BORDER_PX * 2 + _WIDTH_SAFETY_PX) / _UNIT_PX,
        MIN_WIDTH,
    )

    dates_chars = 0
    if options.show_dates:
        if view.birth_date_display is not None:
            dates_chars += len(view.birth_date_display.text)
        if view.death_date_display is not None:
            dates_chars += len(view.death_date_display.text)

    date_column_width = 0.0
    date_column_height = 0.0
    if dates_chars > 0:
        date_column_width = DATE_COLUMN_WIDTH + _PADDING_PX / _UNIT_PX
        date_column_height = dates_chars * (_MAIN_CHAR_PX / _UNIT_PX) + _PADDING_PX * 2 / _UNIT_PX

    photo_height = 0.0
    if options.show_photos and view.has_photo:
        photo_height = PHOTO_GAP + frame_width * PHOTO_ASPECT_RATIO

    return NodeSize(
        width=frame_width + date_column_width,
        height=frame_height,
        frame_width=frame_width,
        date_column_width=date_column_width,
        date_column_height=date_column_height,
        photo_height=photo_height,
    )
