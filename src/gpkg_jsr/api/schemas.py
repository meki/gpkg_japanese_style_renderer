"""API 応答用の pydantic モデル (11_specifications-APIs.md)。"""
from __future__ import annotations

from pydantic import BaseModel

from gpkg_jsr.api.store import ProjectState


class ProjectSummary(BaseModel):
    project_id: str
    filename: str
    people: int
    families: int
    events: int
    objects: int
    notes: int

    @classmethod
    def from_state(cls, state: ProjectState) -> ProjectSummary:
        db = state.db
        return cls(
            project_id=state.id,
            filename=state.filename,
            people=len(db.people),
            families=len(db.families),
            events=len(db.events),
            objects=len(db.objects),
            notes=len(db.notes),
        )


class PersonSummary(BaseModel):
    handle: str
    display_name: str
    birth_date_text: str | None
    death_date_text: str | None
