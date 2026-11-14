import type { AskResponse, DocumentDetail, DocumentListResponse, ErrorDetail, HistoryTurn, InvestigationReport } from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: ErrorDetail | null;

  constructor(status: number, detail: ErrorDetail | null, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function apiBase(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim();
  return (configured || "http://localhost:8000").replace(/\/$/, "");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase()}${path}`, init);
  } catch {
    throw new ApiError(
      0,
      null,
      "The API is not running. From the backend directory, start it with uv run uvicorn app.main:app --reload --port 8000.",
    );
  }
  if (!response.ok) {
    let detail: ErrorDetail | null = null;
    try {
      const body = (await response.json()) as { detail?: ErrorDetail | string };
      if (body.detail && typeof body.detail === "object") {
        detail = body.detail;
      }
    } catch {
      detail = null;
    }
    throw new ApiError(response.status, detail, detail?.message ?? `Request failed (${response.status}).`);
  }
  return (await response.json()) as T;
}

export function getCase(): Promise<{ markdown: string }> {
  return request("/api/case");
}

export function getDocuments(): Promise<DocumentListResponse> {
  return request("/api/documents");
}

export function getDocument(id: string): Promise<DocumentDetail> {
  return request(`/api/documents/${encodeURIComponent(id)}`);
}

export function investigate(): Promise<InvestigationReport> {
  return request("/api/investigate", { method: "POST" });
}

export function ask(question: string, history: HistoryTurn[]): Promise<AskResponse> {
  return request("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });
}
