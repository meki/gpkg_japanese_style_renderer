# Onboarding

## Documentation

All documents are located in the `docs` folder. You can edit them directly in the repository. `docs_templates` contains the templates for the StrictDoc markdown documents. You should follow the templates when editing documents.

Read [00_requirements.md](00_requirements.md) first, then [10_specifications.md](10_specifications.md) and [20_architecture.md](20_architecture.md) (including its ADRs) before making design decisions — several non-obvious constraints (vertical typesetting split, override-based editing, pre-1873 date handling) are recorded there and are easy to re-derive incorrectly from the code alone.

## Example data (`__example_data/`)

`__example_data/` (sample `.gpkg`, sample family-tree images, `GPKG_FORMAT_NOTES.md`) is listed in `.gitignore` and is **not present in every checkout or worktree** — it may exist in the main repository working copy but not in a given git worktree. Do not assume its presence.

Because of this, **automated tests must not depend on `__example_data/`**. `tests/fixtures/minimal_family.gramps.xml` is a small synthetic Gramps XML fixture that reproduces the edge cases discovered by analyzing the real sample data (adoption, remarriage, former surname, kana, birth-order labels, blood type, every date-completeness pattern the format supports, an unlinked nameless person, notes, and a media reference) — see `tests/gramps/test_gpkg_reader.py`. Extend this fixture rather than reaching for the real file when adding tests.

Manual verification against the real sample data (visual review in a browser, layout sanity checks on 136 people / 8 generations) is expected but optional and out of scope for CI.

## Python environment

The project is pinned to Python 3.12 (`.python-version`, `requires-python = ">=3.12"` in `pyproject.toml`) via [uv](https://docs.astral.sh/uv/). Python 3.14 was the original target but is only available locally as a pre-release build (`3.14.0a4`), which `uv` will not resolve against; revisit the pin once 3.14 reaches a stable release.

```bash
uv sync
uv run pytest
uv run ruff check .
uv run mypy src tests
```

## Package layout

```
src/gpkg_jsr/
  gramps/gpkg_reader.py   Gramps .gpkg 読み込み。元 src/gpkg_reader.py を無変更で移設したもの。
                           ruff/mypy の strict ルールは per-file-ignore / override で緩めてある
                           (pyproject.toml を参照) — 新規コードには通常どおり全ルールを適用する。
  model/, format/         Phase 1 以降で追加 (PersonView・DAG・和暦・漢数字変換)
  layout/                 Phase 2 以降で追加 (LayoutResult・自動レイアウト・印刷割付)
  api/                    Phase 3 以降で追加 (FastAPI)
```

現状 `gramps/` のみ実装済み。ディレクトリ構成の全体像は [20_architecture.md](20_architecture.md) の AD-01-02 を参照。
