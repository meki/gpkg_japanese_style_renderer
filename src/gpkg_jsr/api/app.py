"""FastAPI アプリケーション (11_specifications-APIs.md)。

RQ-08-01 (ローカル実行) のため、外部ネットワークへの送信は行わず、CORS は
ローカル開発サーバのオリジンのみを許可する。認証は設けない (単一利用者の
ローカル実行を前提とするため)。
"""
from __future__ import annotations

import tarfile
from xml.etree import ElementTree as ET

from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from gpkg_jsr.api.errors import ApiError, api_error_handler
from gpkg_jsr.api.schemas import PersonSummary, ProjectSummary
from gpkg_jsr.api.store import ProjectNotFoundError, ProjectState, ProjectStore
from gpkg_jsr.layout.engine import build_layout
from gpkg_jsr.layout.types import LayoutResult
from gpkg_jsr.model.view import Calendar

_GPKG_PARSE_ERRORS = (ValueError, OSError, tarfile.TarError, ET.ParseError)

# ローカル Web アプリの開発サーバが使う典型的なオリジン (Vite の既定ポート等)。
_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app = FastAPI(title="gpkg Japanese Style Renderer API")
app.add_exception_handler(ApiError, api_error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = ProjectStore()


def _get_project_or_404(project_id: str) -> ProjectState:
    try:
        return store.get(project_id)
    except ProjectNotFoundError as exc:
        raise ApiError(404, "PROJECT_NOT_FOUND", f"project not found: {exc.project_id}") from exc


@app.post("/api/v1/projects", status_code=201)
async def upload_project(file: UploadFile) -> ProjectSummary:
    """API-01-01: gpkg のアップロード。"""
    gpkg_bytes = await file.read()
    try:
        state = store.add_from_bytes(file.filename or "upload.gpkg", gpkg_bytes)
    except _GPKG_PARSE_ERRORS as exc:
        raise ApiError(422, "GPKG_PARSE_FAILED", str(exc)) from exc
    return ProjectSummary.from_state(state)


@app.get("/api/v1/projects")
async def list_projects() -> list[ProjectSummary]:
    """API-01-02: プロジェクト一覧。"""
    return [ProjectSummary.from_state(state) for state in store.list()]


@app.delete("/api/v1/projects/{project_id}", status_code=204)
async def delete_project(project_id: str) -> None:
    """API-01-03: プロジェクトの破棄。"""
    try:
        store.remove(project_id)
    except ProjectNotFoundError as exc:
        raise ApiError(404, "PROJECT_NOT_FOUND", f"project not found: {exc.project_id}") from exc


@app.get("/api/v1/projects/{project_id}/people")
async def list_people(project_id: str) -> list[PersonSummary]:
    """API-02-02: 起点人物選択 UI 向けの軽量な人物一覧。"""
    state = _get_project_or_404(project_id)
    db = state.db
    result = []
    for person in db.people.values():
        birth = db.birth_date(person)
        death = db.death_date(person)
        result.append(
            PersonSummary(
                handle=person.handle,
                display_name=person.display_name(),
                birth_date_text=birth.format_ja() if birth else None,
                death_date_text=death.format_ja() if death else None,
            )
        )
    return result


@app.get("/api/v1/projects/{project_id}/layout")
async def get_layout(
    project_id: str, root_handle: str | None = None, calendar: Calendar = "wareki"
) -> LayoutResult:
    """API-02-01: レイアウトの取得。

    現時点 (Phase 3) では `layout.engine.build_layout` が単一起点からの子孫方向
    レイアウトのみをサポートするため、`root_handle` を必須とする。「省略時は
    全人物」(RQ-05-01) の対応は Phase 4 以降で拡張する。
    """
    state = _get_project_or_404(project_id)
    if root_handle is None:
        raise ApiError(
            422,
            "ROOT_HANDLE_REQUIRED",
            "root_handle is required in the current implementation; "
            "whole-tree layout (RQ-05-01) is not yet supported",
        )
    root = state.db.get_person(root_handle)
    if root is None:
        raise ApiError(404, "PERSON_NOT_FOUND", f"person not found: {root_handle}")

    return build_layout(
        state.db,
        root,
        calendar=calendar,
        lineage_surnames=state.lineage_surnames,
    )


@app.get("/api/v1/projects/{project_id}/media/{object_handle}")
async def get_media(project_id: str, object_handle: str) -> Response:
    """API-03-01: 顔写真等のメディア実データの取得。"""
    state = _get_project_or_404(project_id)
    media = state.db.objects.get(object_handle)
    if media is None:
        raise ApiError(404, "MEDIA_NOT_FOUND", f"media object not found: {object_handle}")
    data = state.db.media_bytes(media)
    if data is None:
        raise ApiError(404, "MEDIA_NOT_FOUND", f"media bytes not found: {object_handle}")
    return Response(content=data, media_type=media.mime or "application/octet-stream")


@app.get("/api/v1/projects/{project_id}/people/{person_handle}/photo")
async def get_person_photo(project_id: str, person_handle: str) -> Response:
    """API-03-02: 人物 handle から直接、先頭のメディアを取得する。"""
    state = _get_project_or_404(project_id)
    person = state.db.get_person(person_handle)
    if person is None:
        raise ApiError(404, "PERSON_NOT_FOUND", f"person not found: {person_handle}")
    data = state.db.photo_bytes(person)
    if data is None:
        raise ApiError(404, "MEDIA_NOT_FOUND", f"no photo available for person: {person_handle}")
    mime = "application/octet-stream"
    if person.objrefs:
        media = state.db.objects.get(person.objrefs[0])
        if media is not None and media.mime:
            mime = media.mime
    return Response(content=data, media_type=mime)
