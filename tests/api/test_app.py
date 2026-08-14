from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import gpkg_jsr.api.app as app_module
from gpkg_jsr.api.store import ProjectStore


@pytest.fixture
def client() -> Iterator[TestClient]:
    # ルートハンドラはモジュールグローバルの `store` を参照するため、
    # テストごとに差し替えて状態を分離する。
    app_module.store = ProjectStore()
    yield TestClient(app_module.app)


@pytest.fixture
def uploaded_project_id(client: TestClient, minimal_family_gpkg_bytes: bytes) -> str:
    response = client.post(
        "/api/v1/projects",
        files={"file": ("minimal_family.gpkg", minimal_family_gpkg_bytes, "application/gzip")},
    )
    assert response.status_code == 201
    project_id: str = response.json()["project_id"]
    return project_id


class TestUpload:
    def test_valid_gpkg_returns_summary(
        self, client: TestClient, minimal_family_gpkg_bytes: bytes
    ) -> None:
        response = client.post(
            "/api/v1/projects",
            files={
                "file": ("minimal_family.gpkg", minimal_family_gpkg_bytes, "application/gzip")
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["filename"] == "minimal_family.gpkg"
        assert body["people"] == 10
        assert body["families"] == 3
        assert body["events"] == 10
        assert body["objects"] == 1
        assert body["notes"] == 1
        assert "project_id" in body

    def test_invalid_gpkg_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/projects",
            files={"file": ("garbage.gpkg", b"not a valid gpkg archive", "application/gzip")},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "GPKG_PARSE_FAILED"


class TestProjectList:
    def test_empty_store_returns_empty_list(self, client: TestClient) -> None:
        response = client.get("/api/v1/projects")
        assert response.status_code == 200
        assert response.json() == []

    def test_lists_uploaded_project(self, client: TestClient, uploaded_project_id: str) -> None:
        response = client.get("/api/v1/projects")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["project_id"] == uploaded_project_id


class TestProjectDeletion:
    def test_delete_removes_project(self, client: TestClient, uploaded_project_id: str) -> None:
        response = client.delete(f"/api/v1/projects/{uploaded_project_id}")
        assert response.status_code == 204

        response = client.get(f"/api/v1/projects/{uploaded_project_id}/people")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"

    def test_delete_nonexistent_project_returns_404(self, client: TestClient) -> None:
        response = client.delete("/api/v1/projects/does-not-exist")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


class TestPeopleList:
    def test_returns_all_people(self, client: TestClient, uploaded_project_id: str) -> None:
        response = client.get(f"/api/v1/projects/{uploaded_project_id}/people")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 10
        taro = next(p for p in body if p["display_name"] == "山田 太郎")
        assert taro["birth_date_text"] == "1850年3月5日"
        assert taro["death_date_text"] == "1920年以前"

    def test_unknown_project_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/projects/does-not-exist/people")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


class TestLayout:
    def test_missing_root_handle_returns_422(
        self, client: TestClient, uploaded_project_id: str
    ) -> None:
        response = client.get(f"/api/v1/projects/{uploaded_project_id}/layout")
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "ROOT_HANDLE_REQUIRED"

    def test_unknown_root_handle_returns_404(
        self, client: TestClient, uploaded_project_id: str
    ) -> None:
        response = client.get(
            f"/api/v1/projects/{uploaded_project_id}/layout", params={"root_handle": "_p9999"}
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "PERSON_NOT_FOUND"

    def test_valid_root_handle_returns_layout(
        self, client: TestClient, uploaded_project_id: str
    ) -> None:
        response = client.get(
            f"/api/v1/projects/{uploaded_project_id}/layout", params={"root_handle": "_p0001"}
        )
        assert response.status_code == 200
        body = response.json()
        handles = {node["handle"] for node in body["nodes"]}
        assert handles == {
            "_p0001",
            "_p0002",
            "_p0003",
            "_p0004",
            "_p0005",
            "_p0006",
            "_p0007",
            "_p0008",
            "_p0010",
        }
        assert len(body["marriage_edges"]) == 3
        assert len(body["child_edges"]) == 5

    def test_calendar_query_param_selects_wareki_by_default(
        self, client: TestClient, uploaded_project_id: str
    ) -> None:
        response = client.get(
            f"/api/v1/projects/{uploaded_project_id}/layout", params={"root_handle": "_p0003"}
        )
        body = response.json()
        jiro = next(n for n in body["nodes"] if n["handle"] == "_p0003")
        assert jiro["view"]["birth_date_display"]["calendar"] == "wareki"


class TestMedia:
    def test_unknown_object_handle_returns_404(
        self, client: TestClient, uploaded_project_id: str
    ) -> None:
        response = client.get(f"/api/v1/projects/{uploaded_project_id}/media/_o9999")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "MEDIA_NOT_FOUND"

    def test_known_object_without_archived_bytes_returns_404(
        self, client: TestClient, uploaded_project_id: str
    ) -> None:
        # _o0001 のメタデータは存在するが、テスト用 .gpkg には実ファイルを
        # 同梱していないため bytes は取得できない (実運用では取得できるケース)。
        response = client.get(f"/api/v1/projects/{uploaded_project_id}/media/_o0001")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "MEDIA_NOT_FOUND"
