"""アップロードされたプロジェクトのインメモリ管理 (API-01)。

サーバプロセスの生存期間だけ保持し、永続化は行わない (SP-05-04 のプロジェクト
保存とは別の関心事。Phase 4 で別途 API-04 として実装する)。
"""
from __future__ import annotations

import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from gpkg_jsr.format.name_rules import infer_lineage_surnames
from gpkg_jsr.gramps.gpkg_reader import GrampsDatabase


class ProjectNotFoundError(Exception):
    def __init__(self, project_id: str) -> None:
        super().__init__(f"project not found: {project_id}")
        self.project_id = project_id


@dataclass
class ProjectState:
    id: str
    filename: str
    db: GrampsDatabase
    lineage_surnames: frozenset[str]


class ProjectStore:
    def __init__(self) -> None:
        self._projects: dict[str, ProjectState] = {}

    def add_from_bytes(self, filename: str, gpkg_bytes: bytes) -> ProjectState:
        """gpkg のバイト列からプロジェクトを構築する。

        `GrampsDatabase.load()` はパス入力のみを受け付けるため、一時ファイルへ
        書き出してから読み込む。パース失敗時の例外はそのまま呼び出し側へ伝播する
        (API 層で ApiError へ変換する)。
        """
        with tempfile.NamedTemporaryFile(suffix=".gpkg", delete=False) as tmp:
            tmp.write(gpkg_bytes)
            tmp_path = Path(tmp.name)
        try:
            db = GrampsDatabase.load(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

        project_id = uuid.uuid4().hex
        lineage = infer_lineage_surnames(db.people.values())
        state = ProjectState(id=project_id, filename=filename, db=db, lineage_surnames=lineage)
        self._projects[project_id] = state
        return state

    def get(self, project_id: str) -> ProjectState:
        try:
            return self._projects[project_id]
        except KeyError:
            raise ProjectNotFoundError(project_id) from None

    def list(self) -> list[ProjectState]:
        return list(self._projects.values())

    def remove(self, project_id: str) -> None:
        try:
            del self._projects[project_id]
        except KeyError:
            raise ProjectNotFoundError(project_id) from None
