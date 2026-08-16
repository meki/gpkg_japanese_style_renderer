// 11_specifications-APIs.md のエンドポイントに対応する fetch ラッパー。
// vite.config.ts の dev proxy で /api は FastAPI (127.0.0.1:8001) へ転送される。

import type { Calendar, LayoutResult, PersonNode } from "../types/layout";

// Compatibility fallback for layout responses produced before photo_height was
// included in the LayoutResult payload. Keep these values aligned with
// src/gpkg_jsr/layout/metrics.py until all running backends are current.
const LEGACY_PHOTO_GAP = 0.15;
const LEGACY_PHOTO_ASPECT_RATIO = 1.25;

export interface ProjectSummary {
  project_id: string;
  filename: string;
  people: number;
  families: number;
  events: number;
  objects: number;
  notes: number;
}

export interface PersonSummary {
  handle: string;
  display_name: string;
  birth_date_text: string | null;
  death_date_text: string | null;
}

interface ApiErrorBody {
  error: { code: string; message: string };
}

export class ApiError extends Error {
  readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = "ApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await response.json()) as ApiErrorBody;
    throw new ApiError(body.error.code, body.error.message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

function normalizePersonNode(node: PersonNode): PersonNode {
  const dateColumnWidth =
    typeof node.date_column_width === "number" && Number.isFinite(node.date_column_width)
      ? node.date_column_width
      : 0;
  const photoHeight =
    typeof node.photo_height === "number" && Number.isFinite(node.photo_height)
      ? node.photo_height
      : node.view.has_photo
        ? LEGACY_PHOTO_GAP + node.width * LEGACY_PHOTO_ASPECT_RATIO
        : 0;
  return { ...node, date_column_width: dateColumnWidth, photo_height: photoHeight };
}

/** Normalize layout payloads from older backends before they reach render code. */
export function normalizeLayoutResult(layout: LayoutResult): LayoutResult {
  return {
    ...layout,
    nodes: layout.nodes.map(normalizePersonNode),
    auxiliary_nodes: layout.auxiliary_nodes.map(normalizePersonNode),
  };
}

export async function uploadProject(file: File): Promise<ProjectSummary> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/v1/projects", { method: "POST", body: formData });
  return handleResponse<ProjectSummary>(response);
}

export async function listPeople(projectId: string): Promise<PersonSummary[]> {
  const response = await fetch(`/api/v1/projects/${projectId}/people`);
  return handleResponse<PersonSummary[]>(response);
}

export async function getLayout(
  projectId: string,
  rootHandle: string,
  calendar: Calendar = "wareki",
): Promise<LayoutResult> {
  const params = new URLSearchParams({ root_handle: rootHandle, calendar });
  const response = await fetch(`/api/v1/projects/${projectId}/layout?${params.toString()}`);
  return normalizeLayoutResult(await handleResponse<LayoutResult>(response));
}

export function personPhotoUrl(projectId: string, personHandle: string): string {
  return `/api/v1/projects/${projectId}/people/${personHandle}/photo`;
}
