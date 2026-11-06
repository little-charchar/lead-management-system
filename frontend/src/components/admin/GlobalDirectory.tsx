"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  Download,
  FileSearch,
  RefreshCw,
  Search,
  UserRoundCog,
  X,
} from "lucide-react";

import {
  api,
  type ApiError,
  type CaseListRecord,
  type CaseRecord,
  type CaseStatus,
  type LawFirm,
  type Lead,
  type LeadStatus,
} from "@/lib/api";
import { Button, Card, InlineMessage, StatusPill } from "@/components/ui";
import { FirmPicker } from "@/components/admin/FirmPicker";
import { Pagination } from "@/components/Pagination";
import { DrawerPortal } from "@/components/DrawerPortal";

const leadStatuses: LeadStatus[] = [
  "UNASSIGNED",
  "PENDING_REVIEW",
  "DECLINED",
];
const caseStatuses: CaseStatus[] = [
  "INTAKE",
  "INVESTIGATION",
  "DISCOVERY",
  "SETTLED",
  "CLOSED",
];
const PAGE_SIZE = 10;

export function GlobalDirectory({
  onInspect,
  onReassignLead,
  onReassignCase,
  refreshKey = 0,
}: {
  onInspect: (
    entity: { type: "LEAD" | "CASE"; id: number },
    lead?: Lead,
  ) => void;
  onReassignLead: (lead: Lead, firms: LawFirm[]) => void;
  onReassignCase: (record: CaseRecord, firms: LawFirm[]) => void;
  refreshKey?: number;
}) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [cases, setCases] = useState<CaseListRecord[]>([]);
  const [firms, setFirms] = useState<LawFirm[]>([]);
  const [leadStatus, setLeadStatus] = useState<LeadStatus | "ALL">("ALL");
  const [caseStatus, setCaseStatus] = useState<CaseStatus | "ALL">("ALL");
  const [caseSearchInput, setCaseSearchInput] = useState("");
  const [caseSearch, setCaseSearch] = useState("");
  const [leadPage, setLeadPage] = useState(0);
  const [casePage, setCasePage] = useState(0);
  const [leadTotal, setLeadTotal] = useState(0);
  const [caseTotal, setCaseTotal] = useState(0);
  const [firmId, setFirmId] = useState("");
  const [search, setSearch] = useState("");
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [selectedCase, setSelectedCase] = useState<CaseRecord | null>(null);
  const [selectedLeadCase, setSelectedLeadCase] = useState<CaseRecord | null>(null);
  const [loadingLeadCase, setLoadingLeadCase] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    const leadSearchTerm = search.trim().length >= 2 ? search.trim() : undefined;
    const caseSearchTerm =
      caseSearch.trim().length >= 2 ? caseSearch.trim() : undefined;
    try {
      const [leadRecords, caseRecords, firmRecords] = await Promise.all([
        api.fetchLeadPage({
          status: leadStatus === "ALL" ? undefined : leadStatus,
          search: leadSearchTerm,
          assigned_firm_id: firmId ? Number(firmId) : undefined,
          exclude_accepted: true,
          limit: PAGE_SIZE,
          offset: leadPage * PAGE_SIZE,
        }),
        api.fetchAdminCasePage({
          search: caseSearchTerm,
          status: caseStatus === "ALL" ? undefined : caseStatus,
          firm_id: firmId ? Number(firmId) : undefined,
          limit: PAGE_SIZE,
          offset: casePage * PAGE_SIZE,
        }),
        api.fetchFirms(),
      ]);
      setLeads(
        [...leadRecords.items].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        ),
      );
      setLeadTotal(leadRecords.total);
      setCases(caseRecords.items);
      setCaseTotal(caseRecords.total);
      setFirms(firmRecords);
    } catch (reason) {
      setError((reason as ApiError).message ?? "The global directory could not be loaded.");
    } finally {
      setLoading(false);
    }

  }, [casePage, caseSearch, caseStatus, firmId, leadPage, leadStatus, search]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 250);
    return () => window.clearTimeout(timer);
  }, [load, refreshKey]);

  useEffect(() => {
    if (selectedLead === null && selectedCase === null) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeDrawer();
    };
    document.addEventListener("keydown", closeOnEscape);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.body.style.overflow = "";
    };
  }, [selectedCase, selectedLead]);

  useEffect(() => {
    if (selectedLead) {
      const refreshedLead = leads.find((lead) => lead.id === selectedLead.id);
      if (refreshedLead) setSelectedLead(refreshedLead);
    }
  }, [leads, selectedLead]);

  async function openCase(record: CaseListRecord) {
    setSelectedLead(null);
    setSelectedCase(null);
    setError("");
    try {
      setSelectedCase(await api.fetchCase(record.id));
    } catch (reason) {
      setError((reason as ApiError).message ?? "Case details could not be loaded.");
    }
  }

  async function reassignCase(record: CaseListRecord) {
    setError("");
    try {
      onReassignCase(await api.fetchCase(record.id), firms);
    } catch (reason) {
      setError((reason as ApiError).message ?? "Case details could not be loaded.");
    }
  }

  async function openLead(lead: Lead) {
    setSelectedLead(lead);
    setSelectedCase(null);
    setSelectedLeadCase(null);
    if (lead.status !== "ACCEPTED") return;
    setLoadingLeadCase(true);
    try {
      setSelectedLeadCase(await api.fetchCaseForLead(lead.id));
    } catch (reason) {
      setError((reason as ApiError).message ?? "The accepted case could not be loaded.");
    } finally {
      setLoadingLeadCase(false);
    }
  }

  function closeDrawer() {
    setSelectedLead(null);
    setSelectedCase(null);
    setSelectedLeadCase(null);
  }

  function applyCaseSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCasePage(0);
    setCaseSearch(caseSearchInput.trim());
  }

  function downloadCaseDocument(record: CaseRecord, documentId: number, filename: string) {
    void api
      .downloadDocument(record.id, documentId)
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        const anchor = window.document.createElement("a");
        anchor.href = url;
        anchor.download = filename;
        anchor.click();
        window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
      })
      .catch((reason: unknown) =>
        setError((reason as ApiError).message ?? "The document could not be downloaded."),
      );
  }

  function downloadLeadAttachment(lead: Lead, attachmentId: number, filename: string) {
    void api
      .downloadLeadAttachment(lead.id, attachmentId)
      .then((blob) => saveBlob(blob, filename))
      .catch((reason: unknown) =>
        setError((reason as ApiError).message ?? "The lead attachment could not be downloaded."),
      );
  }

  const showingLeadCase = selectedLeadCase;
  const drawerOpen = selectedLead !== null || selectedCase !== null;
  return (
    <>
      <div className="space-y-6">
        <Card id="directory" className="overflow-hidden">
          <div className="flex flex-col gap-4 border-b border-line p-5 sm:px-6 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="flex items-center gap-2 text-forest">
                <UserRoundCog size={17} />
                <p className="text-[10px] font-bold uppercase tracking-[.17em]">System-wide</p>
              </div>
              <h3 className="mt-2 font-serif text-2xl text-ink">Lead directory</h3>
              <p className="mt-1 text-xs text-muted">
                Unaccepted leads awaiting review or assignment. Accepted leads are managed as cases below.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <label className="relative min-w-[220px]">
                <span className="sr-only">Search leads</span>
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
                <input
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    setLeadPage(0);
                    setCasePage(0);
                  }}
                  placeholder="Name, email, title, region"
                  className="field-input pl-9"
                />
              </label>
              <FirmPicker
                firms={firms}
                selectedFirmId={firmId ? Number(firmId) : null}
                placeholder="All firms"
                ariaLabel="Search and filter by firm in both directories"
                onSelect={(firm) => {
                  setFirmId(firm ? String(firm.id) : "");
                  setLeadPage(0);
                  setCasePage(0);
                }}
              />
              <select
                value={leadStatus}
                onChange={(event) => {
                  setLeadStatus(event.target.value as LeadStatus | "ALL");
                  setLeadPage(0);
                }}
                className="field-input w-auto min-w-[155px]"
                aria-label="Filter leads by status"
              >
                <option value="ALL">All unresolved leads</option>
                {leadStatuses.map((status) => (
                  <option key={status} value={status}>{status.replaceAll("_", " ")}</option>
                ))}
              </select>
              <Button type="button" variant="secondary" className="px-3" onClick={() => void load()}>
                <RefreshCw size={15} />
              </Button>
            </div>
          </div>

          {error && <div className="p-5"><InlineMessage tone="error">{error}</InlineMessage></div>}
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-left">
              <thead className="bg-[#fafbf9] text-[10px] uppercase tracking-[.12em] text-muted">
                <tr>
                  <th className="px-6 py-3 font-semibold">Plaintiff / lead</th>
                  <th className="px-4 py-3 font-semibold">Region</th>
                  <th className="px-4 py-3 font-semibold">Assigned firm</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-6 py-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {leads.map((lead) => (
                  <tr
                    key={lead.id}
                    tabIndex={0}
                    onClick={() => void openLead(lead)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        void openLead(lead);
                      }
                    }}
                    className="cursor-pointer hover:bg-[#fcfdfb]"
                  >
                    <td className="px-6 py-4">
                      <p className="text-sm font-semibold text-ink">
                        {lead.plaintiff?.name ?? `Lead #${lead.id}`}
                      </p>
                      <p className="mt-1 text-[11px] text-muted">{lead.title} · #{lead.id}</p>
                    </td>
                    <td className="px-4 py-4 text-sm text-ink">
                      {lead.category.replaceAll("_", " ")} · {lead.region}
                    </td>
                    <td className="px-4 py-4 text-sm text-muted">
                      {lead.assigned_firm?.name ?? "Unassigned"}
                    </td>
                    <td className="px-4 py-4"><StatusPill status={lead.status} /></td>
                    <td className="px-6 py-4">
                      <div className="flex justify-end gap-2">
                        <Button
                          type="button"
                          variant="secondary"
                          className="w-[92px] justify-center px-2 py-2 text-xs"
                          onClick={(event) => {
                            event.stopPropagation();
                            void openLead(lead);
                          }}
                        >
                          View lead
                        </Button>
                        <Button
                          type="button"
                          variant="secondary"
                          className="w-[92px] justify-center px-2 py-2 text-xs"
                          onClick={(event) => {
                            event.stopPropagation();
                            onInspect({ type: "LEAD", id: lead.id }, lead);
                          }}
                        >
                          Audit
                        </Button>
                        {lead.status !== "ACCEPTED" && (
                          <Button
                            type="button"
                            className="w-[92px] justify-center px-2 py-2 text-xs"
                            onClick={(event) => {
                              event.stopPropagation();
                              onReassignLead(lead, firms);
                            }}
                          >
                            {lead.status === "PENDING_REVIEW" ? "Reassign" : "Assign"}
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && leads.length === 0 && (
                  <tr><td colSpan={5} className="px-6 py-10 text-center text-sm text-muted">No leads match this view.</td></tr>
                )}
                {loading && (
                  <tr><td colSpan={5} className="px-6 py-10 text-center text-sm text-muted">Loading directory…</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {leadTotal > 0 && (
            <div className="border-t border-line">
              <p className="px-6 pt-3 text-[11px] text-muted">
                Unassigned and declined leads can be assigned; pending leads can be reassigned.
              </p>
              <Pagination
                page={leadPage}
                pageSize={PAGE_SIZE}
                total={leadTotal}
                label="leads"
                disabled={loading}
                borderTop={false}
                onPageChange={setLeadPage}
              />
            </div>
          )}
        </Card>

        <Card className="overflow-hidden">
          <div className="flex flex-wrap items-end justify-between gap-4 border-b border-line p-5 sm:px-6">
            <div>
              <h3 className="font-serif text-2xl text-ink">Case directory</h3>
              <p className="mt-1 text-xs text-muted">
                Accepted leads are cases. Search by client, title, category, or region; the firm filter above applies here too.
              </p>
            </div>
            <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
              <form onSubmit={applyCaseSearch} className="flex w-full gap-2 sm:w-auto">
                <label className="relative min-w-0 flex-1 sm:w-80">
                  <span className="sr-only">Search cases</span>
                  <Search
                    size={15}
                    className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
                  />
                  <input
                    value={caseSearchInput}
                    onChange={(event) => setCaseSearchInput(event.target.value)}
                    placeholder="Name, email, title, region…"
                    className="field-input pl-9"
                  />
                </label>
                <Button type="submit" variant="secondary" disabled={loading}>
                  Search
                </Button>
              </form>
              <select
                value={caseStatus}
                onChange={(event) => {
                  setCaseStatus(event.target.value as CaseStatus | "ALL");
                  setCasePage(0);
                }}
                className="field-input w-auto min-w-[175px]"
                aria-label="Filter cases by status"
              >
                <option value="ALL">All case statuses</option>
                {caseStatuses.map((status) => (
                  <option key={status} value={status}>{status.replaceAll("_", " ")}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-left">
              <thead className="bg-[#fafbf9] text-[10px] uppercase tracking-[.12em] text-muted">
                <tr>
                  <th className="px-6 py-3 font-semibold">Case</th>
                  <th className="px-4 py-3 font-semibold">Client</th>
                  <th className="px-4 py-3 font-semibold">Category / region</th>
                  <th className="px-4 py-3 font-semibold">Firm</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Updated</th>
                  <th className="px-6 py-3 text-right font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {cases.map((record) => (
                  <tr
                    key={record.id}
                    tabIndex={0}
                    onClick={() => void openCase(record)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        void openCase(record);
                      }
                    }}
                    className="cursor-pointer hover:bg-[#fcfdfb]"
                  >
                    <td className="px-6 py-4">
                      <p className="text-sm font-semibold text-ink">{record.lead.title}</p>
                      <p className="mt-1 text-[11px] text-muted">Case #{record.id}</p>
                    </td>
                    <td className="px-4 py-4 text-sm text-ink">
                      <p>{record.lead.plaintiff?.name ?? "Client"}</p>
                      <p className="mt-1 text-xs text-muted">{record.lead.plaintiff?.email}</p>
                    </td>
                    <td className="px-4 py-4 text-sm text-muted">
                      {record.lead.category.replaceAll("_", " ")} · {record.lead.region}
                    </td>
                    <td className="px-4 py-4 text-sm text-muted">
                      {firms.find((firm) => firm.id === record.assigned_firm_id)?.name ?? `Firm #${record.assigned_firm_id}`}
                    </td>
                    <td className="px-4 py-4"><StatusPill status={record.status} /></td>
                    <td className="px-4 py-4 text-xs text-muted">
                      {new Date(record.updated_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex justify-end gap-2">
                        <Button
                          type="button"
                          variant="secondary"
                          className="w-[92px] justify-center px-2 py-2 text-xs"
                          onClick={(event) => {
                            event.stopPropagation();
                            void openCase(record);
                          }}
                        >
                          View case
                        </Button>
                        <Button
                          type="button"
                          variant="secondary"
                          className="w-[92px] justify-center px-2 py-2 text-xs"
                          onClick={(event) => {
                            event.stopPropagation();
                            onInspect({ type: "CASE", id: record.id });
                          }}
                        >
                          Audit
                        </Button>
                        {record.status !== "CLOSED" && (
                          <Button
                            type="button"
                            className="w-[92px] justify-center px-2 py-2 text-xs"
                            onClick={(event) => {
                              event.stopPropagation();
                              void reassignCase(record);
                            }}
                          >
                            Reassign
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && cases.length === 0 && (
                  <tr><td colSpan={7} className="px-6 py-10 text-center text-sm text-muted">No cases match this view.</td></tr>
                )}
                {loading && (
                  <tr><td colSpan={7} className="px-6 py-10 text-center text-sm text-muted">Loading case directory…</td></tr>
                )}
              </tbody>
            </table>
          </div>
          {caseTotal > 0 && (
            <Pagination
              page={casePage}
              pageSize={PAGE_SIZE}
              total={caseTotal}
              label="cases"
              disabled={loading}
              onPageChange={setCasePage}
            />
          )}
        </Card>
      </div>

      {drawerOpen && (
        <DrawerPortal>
          <button
            type="button"
            aria-label="Close record details"
            onClick={closeDrawer}
            className="absolute inset-0 h-full w-full bg-ink/45 backdrop-blur-[2px]"
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-label={selectedCase ? "Case details" : "Lead details"}
            className="absolute inset-y-0 right-0 flex h-dvh w-full max-w-2xl flex-col bg-[#fbfcfa] shadow-2xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-line bg-white px-5 py-5 sm:px-7">
              <div className="min-w-0">
                <p className="text-[10px] font-bold uppercase tracking-[.16em] text-forest">
                  {selectedCase ? `Case #${selectedCase.id}` : `Lead #${selectedLead?.id}`}
                </p>
                <h2 className="mt-1 break-words font-serif text-2xl text-ink sm:text-3xl">
                  {selectedCase?.lead.title ?? selectedLead?.title}
                </h2>
                <p className="mt-2 text-sm text-muted">
                  {(selectedCase?.lead ?? selectedLead)?.category.replaceAll("_", " ")} ·{" "}
                  {(selectedCase?.lead ?? selectedLead)?.region}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <StatusPill status={selectedCase?.status ?? selectedLead?.status ?? ""} />
                <button
                  type="button"
                  aria-label="Close details"
                  onClick={closeDrawer}
                  className="rounded-xl p-2 text-muted transition hover:bg-canvas hover:text-ink"
                >
                  <X size={20} />
                </button>
              </div>
            </header>
            <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5 sm:p-7">
              {selectedLead && (
                <>
                  <Card className="p-5">
                    <h3 className="text-sm font-bold text-ink">Lead details</h3>
                    <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-muted">
                      {selectedLead.description}
                    </p>
                    <p className="mt-4 border-t border-line pt-3 text-xs text-muted">
                      {selectedLead.plaintiff?.name} · {selectedLead.plaintiff?.email}
                    </p>
                  </Card>
                  {selectedLead.attachments.length > 0 && (
                    <Card className="p-5">
                      <h3 className="text-sm font-bold text-ink">
                        Supporting PDFs ({selectedLead.attachments.length})
                      </h3>
                      <ul className="mt-3 space-y-2">
                        {selectedLead.attachments.map((file) => (
                          <li key={file.id} className="flex items-center gap-2 text-sm">
                            <span className="min-w-0 flex-1 truncate text-ink">{file.file_name}</span>
                            <button
                              type="button"
                              aria-label={`Download ${file.file_name}`}
                              className="rounded-lg p-2 text-muted hover:bg-canvas hover:text-forest"
                              onClick={async () => {
                                try {
                                  const blob = await api.downloadLeadAttachment(selectedLead.id, file.id);
                                  const url = URL.createObjectURL(blob);
                                  const anchor = window.document.createElement("a");
                                  anchor.href = url;
                                  anchor.download = file.file_name;
                                  anchor.click();
                                  window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
                                } catch (reason) {
                                  setError((reason as ApiError).message ?? "Attachment download failed.");
                                }
                              }}
                            >
                              <Download size={16} />
                            </button>
                          </li>
                        ))}
                      </ul>
                    </Card>
                  )}
                  {selectedLead.status === "ACCEPTED" && (
                    loadingLeadCase ? (
                      <p className="text-sm text-muted">Loading associated case…</p>
                    ) : showingLeadCase ? (
                      <CaseDetails
                        record={showingLeadCase}
                        onDownload={downloadCaseDocument}
                        onDownloadLeadAttachment={downloadLeadAttachment}
                      />
                    ) : null
                  )}
                </>
              )}
              {selectedCase && (
                <CaseDetails
                  record={selectedCase}
                  onDownload={downloadCaseDocument}
                  onDownloadLeadAttachment={downloadLeadAttachment}
                />
              )}
              <div className="sticky bottom-0 flex flex-wrap gap-2 border-t border-line bg-[#fbfcfa] py-4">
                {selectedLead && (
                  <>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() =>
                        onInspect({ type: "LEAD", id: selectedLead.id }, selectedLead)
                      }
                    >
                      <FileSearch size={15} /> Audit history
                    </Button>
                    {selectedLead.status !== "ACCEPTED" && (
                      <Button
                        type="button"
                        onClick={() => onReassignLead(selectedLead, firms)}
                      >
                        {selectedLead.status === "PENDING_REVIEW" ? "Reassign lead" : "Assign to firm"}
                      </Button>
                    )}
                  </>
                )}
                {selectedCase && (
                  <>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() => onInspect({ type: "CASE", id: selectedCase.id })}
                    >
                      <FileSearch size={15} /> Audit history
                    </Button>
                    {selectedCase.status !== "CLOSED" && (
                      <Button
                        type="button"
                        onClick={() => onReassignCase(selectedCase, firms)}
                      >
                        Reassign case
                      </Button>
                    )}
                  </>
                )}
              </div>
            </div>
          </aside>
        </DrawerPortal>
      )}
    </>
  );
}

function CaseDetails({
  record,
  onDownload,
  onDownloadLeadAttachment,
}: {
  record: CaseRecord;
  onDownload: (record: CaseRecord, documentId: number, filename: string) => void;
  onDownloadLeadAttachment: (
    lead: Lead,
    attachmentId: number,
    filename: string,
  ) => void;
}) {
  return (
    <>
      <Card className="p-5">
        <h3 className="text-sm font-bold text-ink">Case details</h3>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-muted">
          {record.lead.description}
        </p>
        <div className="mt-4 border-t border-line pt-3">
          <StatusPill status={record.status} />
        </div>
      </Card>
      {record.lead.attachments.length > 0 && (
        <Card className="p-5">
          <h3 className="text-sm font-bold text-ink">Original plaintiff uploads</h3>
          <ul className="mt-3 space-y-2">
            {record.lead.attachments.map((file) => (
              <li key={file.id} className="flex items-center gap-2 text-sm">
                <span className="min-w-0 flex-1 truncate text-ink">{file.file_name}</span>
                <button
                  type="button"
                  aria-label={`Download ${file.file_name}`}
                  onClick={() =>
                    onDownloadLeadAttachment(record.lead, file.id, file.file_name)
                  }
                  className="rounded-lg p-2 text-muted hover:bg-canvas hover:text-forest"
                >
                  <Download size={16} />
                </button>
              </li>
            ))}
          </ul>
        </Card>
      )}
      <Card className="p-5">
        <h3 className="text-sm font-bold text-ink">Shared case documents</h3>
        {record.documents.length > 0 ? (
          <ul className="mt-3 space-y-2">
            {record.documents.map((document) => (
              <li key={document.id} className="flex items-center gap-2 text-sm">
                <span className="min-w-0 flex-1 truncate text-ink">{document.file_name}</span>
                <button
                  type="button"
                  aria-label={`Download ${document.file_name}`}
                  onClick={() => onDownload(record, document.id, document.file_name)}
                  className="rounded-lg p-2 text-muted hover:bg-canvas hover:text-forest"
                >
                  <Download size={16} />
                </button>
              </li>
            ))}
          </ul>
        ) : <p className="mt-3 text-sm text-muted">No case documents.</p>}
      </Card>
      <Card className="p-5">
        <h3 className="text-sm font-bold text-ink">Historical private notes · all firms</h3>
        {record.notes?.length ? (
          <ul className="mt-3 space-y-3">
            {record.notes.map((note) => (
              <li key={note.id} className="rounded-xl bg-canvas p-3">
                <p className="whitespace-pre-wrap text-sm leading-6 text-ink">{note.content}</p>
                <p className="mt-2 text-[10px] text-muted">
                  {note.author?.name ?? "Former staff"} · Firm #{note.author_firm_id} ·{" "}
                  {new Date(note.created_at).toLocaleString()}
                </p>
              </li>
            ))}
          </ul>
        ) : <p className="mt-3 text-sm text-muted">No historical notes.</p>}
      </Card>
    </>
  );
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
}
