// 11_specifications-APIs.md のエンドポイントに対応する fetch ラッパー。
// vite.config.ts の dev proxy で /api は FastAPI (127.0.0.1:8001) へ転送される。

import type { Calendar, LayoutResult } from "../types/layout";

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
  return handleResponse<LayoutResult>(response);
}

export function personPhotoUrl(projectId: string, personHandle: string): string {
  return `/api/v1/projects/${projectId}/people/${personHandle}/photo`;
}
