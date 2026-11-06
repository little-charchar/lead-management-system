/** Typed fetch client for the FastAPI backend. */

export type UserRole = "PLAINTIFF" | "ATTORNEY" | "PARALEGAL" | "ADMIN";
export type LeadStatus =
  | "UNASSIGNED"
  | "PENDING_REVIEW"
  | "ACCEPTED"
  | "DECLINED";
export type CaseStatus =
  | "INTAKE"
  | "INVESTIGATION"
  | "DISCOVERY"
  | "SETTLED"
  | "CLOSED";
export type AuditAction =
  | "AUTO_ROUTED"
  | "ACCEPTED"
  | "DECLINED"
  | "REASSIGNED"
  | "STATUS_CHANGED";

export interface UserSummary {
  id: number;
  name: string;
  email: string;
  role: UserRole;
  law_firm_id: number | null;
}

export interface LawFirm {
  id: number;
  name: string;
  created_at: string;
}

export interface Lead {
  id: number;
  plaintiff_id: number;
  title: string;
  category: string;
  region: string;
  description: string;
  status: LeadStatus;
  assigned_firm_id: number | null;
  created_at: string;
  updated_at: string;
  plaintiff?: UserSummary | null;
  assigned_firm?: LawFirm | null;
  attachments: LeadAttachment[];
}

export interface DocumentUploader {
  id: number;
  name: string;
  role: UserRole;
  law_firm_id: number | null;
  law_firm_name: string | null;
}

export interface LeadAttachment {
  id: number;
  lead_id: number;
  uploaded_by_id: number | null;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  created_at: string;
  uploader?: DocumentUploader | null;
}

export interface DocumentRecord {
  id: number;
  case_id: number;
  uploaded_by_id: number | null;
  file_name: string;
  file_size_bytes: number;
  mime_type: string;
  created_at: string;
  uploader?: DocumentUploader | null;
}

export interface PrivateNote {
  id: number;
  case_id: number;
  author_id: number | null;
  author_firm_id: number;
  content: string;
  created_at: string;
  author?: UserSummary | null;
}

export interface CaseRecord {
  id: number;
  lead_id: number;
  assigned_firm_id: number;
  status: CaseStatus;
  created_at: string;
  updated_at: string;
  lead: Lead;
  documents: DocumentRecord[];
  notes?: PrivateNote[];
}

export interface CaseListRecord {
  id: number;
  lead_id: number;
  assigned_firm_id: number;
  status: CaseStatus;
  created_at: string;
  updated_at: string;
  lead: Pick<
    Lead,
    | "id"
    | "plaintiff_id"
    | "title"
    | "category"
    | "region"
    | "status"
    | "assigned_firm_id"
    | "created_at"
    | "updated_at"
  > & {
    plaintiff?: UserSummary | null;
    assigned_firm?: LawFirm | null;
  };
  document_count: number;
}

export interface AuditLog {
  id: number;
  entity_type: "LEAD" | "CASE";
  entity_id: number;
  actor_id: number | null;
  action: AuditAction;
  previous_state: Record<string, unknown> | null;
  new_state: Record<string, unknown>;
  created_at: string;
  actor?: UserSummary | null;
}

export interface LeadSubmission {
  plaintiff_name: string;
  email: string;
  title: string;
  category: string;
  region: string;
  description: string;
}

export interface PageResult<T> {
  items: T[];
  total: number;
}

const configuredApiUrl = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");
const API_BASE_URL = configuredApiUrl.endsWith("/api")
  ? configuredApiUrl
  : `${configuredApiUrl}/api`;

let activePersonaEmail: string | null = "jane@plaintiff.com";

/** Set by AuthContext; all subsequent API calls use this persona. */
export function setApiPersona(email: string | null): void {
  activePersonaEmail = email;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function openPdfPreview(loadPdf: () => Promise<Blob>): Promise<void> {
  const previewWindow = window.open("about:blank", "_blank");
  if (!previewWindow) {
    throw new Error("Allow pop-ups to preview this PDF.");
  }
  try {
    const blob = await loadPdf();
    const url = URL.createObjectURL(blob);
    previewWindow.location.replace(url);
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
  } catch (reason) {
    previewWindow.close();
    throw reason;
  }
}

async function fetchResponse(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (activePersonaEmail) {
    headers.set("X-Demo-User-Email", activePersonaEmail);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = await response.text();
    }
    const message =
      typeof detail === "object" &&
      detail !== null &&
      "detail" in detail &&
      typeof detail.detail === "string"
        ? detail.detail
        : `Request failed (${response.status})`;
    throw new ApiError(message, response.status, detail);
  }

  return response;
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetchResponse(path, init);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function requestPage<T>(path: string): Promise<PageResult<T>> {
  const response = await fetchResponse(path);
  const items = (await response.json()) as T[];
  const headerTotal = response.headers.get("X-Total-Count");
  const total = headerTotal === null ? items.length : Number(headerTotal);
  if (!Number.isSafeInteger(total) || total < 0) {
    throw new Error("The server returned an invalid pagination total.");
  }
  return { items, total };
}

function queryString(
  params: Record<string, string | number | boolean | undefined>,
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && String(value).length > 0) {
      search.set(key, String(value));
    }
  }
  const serialized = search.toString();
  return serialized ? `?${serialized}` : "";
}

export const api = {
  submitLead: (payload: LeadSubmission) =>
    request<Lead>("/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  fetchLeads: (filters: {
    status?: LeadStatus;
    category?: string;
    region?: string;
    search?: string;
    assigned_firm_id?: number;
    exclude_accepted?: boolean;
    limit?: number;
    offset?: number;
  } = {}) =>
    request<Lead[]>(`/leads${queryString(filters)}`),

  fetchLeadPage: (filters: {
    status?: LeadStatus;
    category?: string;
    region?: string;
    search?: string;
    assigned_firm_id?: number;
    exclude_accepted?: boolean;
    limit?: number;
    offset?: number;
  } = {}) =>
    requestPage<Lead>(`/leads${queryString(filters)}`),

  fetchInbox: (filters: {
    search?: string;
    category?: string;
    region?: string;
    offset?: number;
    limit?: number;
  } = {}) =>
    request<Lead[]>(
      `/leads${queryString({ status: "PENDING_REVIEW", ...filters })}`,
    ),

  fetchInboxPage: (filters: {
    search?: string;
    category?: string;
    region?: string;
    offset?: number;
    limit?: number;
  } = {}) =>
    requestPage<Lead>(
      `/leads${queryString({ status: "PENDING_REVIEW", ...filters })}`,
    ),

  acceptLead: (leadId: number) =>
    request<CaseRecord>(`/leads/${leadId}/accept`, { method: "POST" }),

  declineLead: (leadId: number) =>
    request<Lead>(`/leads/${leadId}/decline`, { method: "POST" }),

  fetchCase: (caseId: number) =>
    request<CaseRecord>(`/cases/${caseId}`),

  fetchFirmCases: (filters: {
    search?: string;
    status?: CaseStatus;
    include_closed?: boolean;
    offset?: number;
    limit?: number;
  } = {}) =>
    request<CaseListRecord[]>(`/cases${queryString(filters)}`),

  fetchFirmCasePage: (filters: {
    search?: string;
    status?: CaseStatus;
    include_closed?: boolean;
    offset?: number;
    limit?: number;
  } = {}) =>
    requestPage<CaseListRecord>(`/cases${queryString(filters)}`),

  fetchPlaintiffCasePage: (filters: {
    search?: string;
    offset?: number;
    limit?: number;
  } = {}) =>
    requestPage<CaseListRecord>(`/cases/mine${queryString(filters)}`),

  fetchCaseForLead: (leadId: number) =>
    request<CaseRecord>(`/leads/${leadId}/case`),

  uploadLeadAttachment: (leadId: number, file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<LeadAttachment>(`/leads/${leadId}/attachments`, {
      method: "POST",
      body,
    });
  },

  downloadLeadAttachment: async (leadId: number, attachmentId: number) => {
    const headers = new Headers();
    if (activePersonaEmail) {
      headers.set("X-Demo-User-Email", activePersonaEmail);
    }
    const response = await fetch(
      `${API_BASE_URL}/leads/${leadId}/attachments/${attachmentId}`,
      { headers, cache: "no-store" },
    );
    if (!response.ok) {
      let detail: unknown;
      try {
        detail = await response.json();
      } catch {
        detail = await response.text();
      }
      const message =
        typeof detail === "object" &&
        detail !== null &&
        "detail" in detail &&
        typeof detail.detail === "string"
          ? detail.detail
          : `Download failed (${response.status})`;
      throw new ApiError(message, response.status, detail);
    }
    return response.blob();
  },

  updateCaseStatus: (caseId: number, status: CaseStatus) =>
    request<CaseRecord>(`/cases/${caseId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    }),

  createNote: (caseId: number, content: string) =>
    request<PrivateNote>(`/cases/${caseId}/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    }),

  uploadDocument: (caseId: number, file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<DocumentRecord>(`/cases/${caseId}/documents`, {
      method: "POST",
      body,
    });
  },

  downloadDocument: async (caseId: number, documentId: number) => {
    const headers = new Headers();
    if (activePersonaEmail) {
      headers.set("X-Demo-User-Email", activePersonaEmail);
    }
    const response = await fetch(
      `${API_BASE_URL}/cases/${caseId}/documents/${documentId}`,
      { headers, cache: "no-store" },
    );
    if (!response.ok) {
      const body = await response.json().catch(() => undefined);
      throw new ApiError(
        body?.detail ?? `Download failed (${response.status})`,
        response.status,
        body,
      );
    }
    return response.blob();
  },

  reassignLead: (leadId: number, targetFirmId: number) =>
    request<Lead>(`/admin/leads/${leadId}/reassign`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target_firm_id: targetFirmId }),
    }),

  reassignCase: (caseId: number, targetFirmId: number) =>
    request<{
      id: number;
      lead_id: number;
      assigned_firm_id: number;
      status: CaseStatus;
    }>(
      `/admin/cases/${caseId}/reassign`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_firm_id: targetFirmId }),
      },
    ),

  fetchFirms: () => request<LawFirm[]>("/admin/firms"),

  fetchAdminCases: (filters: {
    search?: string;
    status?: CaseStatus;
    firm_id?: number;
    limit?: number;
    offset?: number;
  } = {}) =>
    request<CaseListRecord[]>(`/admin/cases${queryString(filters)}`),

  fetchAdminCasePage: (filters: {
    search?: string;
    status?: CaseStatus;
    firm_id?: number;
    limit?: number;
    offset?: number;
  } = {}) =>
    requestPage<CaseListRecord>(`/admin/cases${queryString(filters)}`),

  fetchAuditLogs: (entityType?: "LEAD" | "CASE", entityId?: number) =>
    request<AuditLog[]>(
      `/admin/audit-logs${queryString({ entity_type: entityType, entity_id: entityId, limit: 100 })}`,
    ),
};
