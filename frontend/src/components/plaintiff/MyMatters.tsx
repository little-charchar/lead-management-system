"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import {
  Briefcase,
  Clock3,
  FileCheck2,
  FolderOpen,
  Search,
  X,
} from "lucide-react";

import {
  api,
  type ApiError,
  type CaseListRecord,
  type CaseRecord,
  type Lead,
} from "@/lib/api";
import {
  Button,
  Card,
  EmptyState,
  InlineMessage,
  StatusPill,
} from "@/components/ui";
import { DocumentExchange } from "@/components/plaintiff/DocumentExchange";
import { Pagination } from "@/components/Pagination";
import { DrawerPortal } from "@/components/DrawerPortal";

const PAGE_SIZE = 10;

export function MyMatters({ refreshKey = 0 }: { refreshKey?: number }) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [cases, setCases] = useState<CaseListRecord[]>([]);
  const [unresolvedTotal, setUnresolvedTotal] = useState(0);
  const [pendingTotal, setPendingTotal] = useState(0);
  const [caseTotal, setCaseTotal] = useState(0);
  const [leadSearch, setLeadSearch] = useState("");
  const [caseSearch, setCaseSearch] = useState("");
  const [leadQuery, setLeadQuery] = useState("");
  const [caseQuery, setCaseQuery] = useState("");
  const [leadPage, setLeadPage] = useState(0);
  const [casePage, setCasePage] = useState(0);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [selectedCase, setSelectedCase] = useState<CaseRecord | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const requestId = useRef(0);

  const loadLeads = useCallback(async () => {
    const currentRequestId = ++requestId.current;
    setError("");
    try {
      const [leadsResult, pendingResult, casesResult] = await Promise.all([
        api.fetchLeadPage({
          exclude_accepted: true,
          search: leadQuery.length >= 2 ? leadQuery : undefined,
          limit: PAGE_SIZE,
          offset: leadPage * PAGE_SIZE,
        }),
        api.fetchLeadPage({ status: "PENDING_REVIEW", limit: 1 }),
        api.fetchPlaintiffCasePage({
          search: caseQuery.length >= 2 ? caseQuery : undefined,
          limit: PAGE_SIZE,
          offset: casePage * PAGE_SIZE,
        }),
      ]);
      if (currentRequestId !== requestId.current) return;
      setLeads(leadsResult.items);
      setUnresolvedTotal(leadsResult.total);
      setPendingTotal(pendingResult.total);
      setCases(casesResult.items);
      setCaseTotal(casesResult.total);
    } catch (reason) {
      if (currentRequestId !== requestId.current) return;
      setError((reason as ApiError).message ?? "Your leads could not be loaded.");
    } finally {
      if (currentRequestId === requestId.current) setBusy(false);
    }
  }, [casePage, caseQuery, leadPage, leadQuery]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadLeads(), 0);
    return () => window.clearTimeout(timer);
  }, [refreshKey, loadLeads]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setLeadPage(0);
      setLeadQuery(leadSearch.trim());
    }, 300);
    return () => window.clearTimeout(timer);
  }, [leadSearch]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setCasePage(0);
      setCaseQuery(caseSearch.trim());
    }, 300);
    return () => window.clearTimeout(timer);
  }, [caseSearch]);

  useEffect(() => {
    if (!selectedLead) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeDetails();
    };
    document.addEventListener("keydown", closeOnEscape);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.body.style.overflow = "";
    };
  }, [selectedLead]);

  function closeDetails() {
    setSelectedLead(null);
    setSelectedCase(null);
  }

  function openLead(lead: Lead) {
    setSelectedLead(lead);
    setSelectedCase(null);
  }

  async function openCase(record: CaseListRecord) {
    setSelectedLead(null);
    setSelectedCase(null);
    setError("");
    try {
      const details = await api.fetchCase(record.id);
      setSelectedLead(details.lead);
      setSelectedCase(details);
    } catch (reason) {
      setError((reason as ApiError).message ?? "Case details could not be loaded.");
    }
  }

  return (
    <>
      <div className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <Metric icon={<FileCheck2 size={17} />} label="Unresolved leads" value={unresolvedTotal} />
          <Metric icon={<Briefcase size={17} />} label="Accepted cases" value={caseTotal} />
          <Metric
            icon={<Clock3 size={17} />}
            label="In review"
            value={pendingTotal}
          />
        </div>

        <Card className="overflow-hidden">
          <div className="border-b border-line px-5 py-4 sm:px-6">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h3 className="font-serif text-xl text-ink">Submitted leads</h3>
                <p className="mt-1 text-xs text-muted">Leads awaiting a decision</p>
              </div>
              <label className="relative w-full sm:w-72">
                <span className="sr-only">Search submitted leads</span>
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
                <input
                  type="search"
                  value={leadSearch}
                  onChange={(event) => {
                    setLeadSearch(event.target.value);
                    setLeadPage(0);
                  }}
                  placeholder="Search title, category, region…"
                  className="field-input pl-9"
                />
              </label>
            </div>
          </div>
          {error ? (
            <div className="p-5"><InlineMessage tone="error">{error}</InlineMessage></div>
          ) : busy ? (
            <div className="p-6 text-sm text-muted">Loading your leads…</div>
          ) : unresolvedTotal === 0 && !leadQuery ? (
            <EmptyState
              icon={<FileCheck2 size={22} />}
              title="No unresolved leads"
              description="New submissions appear here while they await a decision."
            />
          ) : leads.length === 0 ? (
            <EmptyState
              icon={<Search size={22} />}
              title="No matching leads"
              description="Try another title, category, or region."
            />
          ) : (
            <div className="divide-y divide-line">
              {leads.map((lead) => (
                <button
                  key={lead.id}
                  type="button"
                  onClick={() => openLead(lead)}
                  className="flex w-full flex-wrap items-center gap-4 px-5 py-4 text-left transition hover:bg-canvas/70 sm:px-6"
                >
                  <div className="grid h-10 w-10 place-items-center rounded-xl bg-canvas text-forest">
                    <FileCheck2 size={18} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-ink">
                      {lead.title}
                    </p>
                    <p className="mt-1 truncate text-xs text-muted">
                      {lead.category.replaceAll("_", " ")} · {lead.region} ·{" "}
                      {new Date(lead.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <StatusPill status={lead.status} />
                </button>
              ))}
            </div>
          )}
          {!error && !busy && unresolvedTotal > 0 && (
            <Pagination
              page={leadPage}
              pageSize={PAGE_SIZE}
              total={unresolvedTotal}
              onPageChange={setLeadPage}
              label="leads"
            />
          )}
        </Card>

        <Card className="overflow-hidden">
          <div className="border-b border-line px-5 py-4 sm:px-6">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <h3 className="font-serif text-xl text-ink">Accepted cases</h3>
                <p className="mt-1 text-xs text-muted">Cases accepted by a law firm</p>
              </div>
              <label className="relative w-full sm:w-72">
                <span className="sr-only">Search accepted cases</span>
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
                <input
                  type="search"
                  value={caseSearch}
                  onChange={(event) => {
                    setCaseSearch(event.target.value);
                    setCasePage(0);
                  }}
                  placeholder="Search title, category, region…"
                  className="field-input pl-9"
                />
              </label>
            </div>
          </div>
          {busy ? (
            <div className="p-6 text-sm text-muted">Loading accepted cases…</div>
          ) : caseTotal === 0 && !caseQuery ? (
            <EmptyState
              icon={<Briefcase size={22} />}
              title="No accepted cases yet"
              description="When a legal team accepts one of your leads, its case will appear here."
            />
          ) : cases.length === 0 ? (
            <EmptyState
              icon={<Search size={22} />}
              title="No matching cases"
              description="Try another title, category, region, or status."
            />
          ) : (
            <div className="divide-y divide-line">
              {cases.map((record) => (
                <button
                  key={record.id}
                  type="button"
                  onClick={() => openCase(record)}
                  className="flex w-full flex-wrap items-center gap-4 px-5 py-4 text-left transition hover:bg-canvas/70 sm:px-6"
                >
                  <div className="grid h-10 w-10 place-items-center rounded-xl bg-mint text-forest">
                    <Briefcase size={18} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-ink">
                      {record.lead.title}
                    </p>
                    <p className="mt-1 text-xs text-muted">
                      {record.lead.category.replaceAll("_", " ")} · {record.lead.region} ·{" "}
                      {record.lead.assigned_firm?.name ?? "Firm assignment pending"} ·{" "}
                      {record.document_count} shared document{record.document_count === 1 ? "" : "s"}
                    </p>
                  </div>
                  <StatusPill status={record.status} />
                </button>
              ))}
            </div>
          )}
          {!busy && !error && caseTotal > 0 && (
            <Pagination
              page={casePage}
              pageSize={PAGE_SIZE}
              total={caseTotal}
              onPageChange={setCasePage}
              label="cases"
            />
          )}
        </Card>
      </div>

      {selectedLead && (
        <DrawerPortal>
          <button
            type="button"
            aria-label="Close lead details"
            onClick={closeDetails}
            className="absolute inset-0 h-full w-full bg-ink/45 backdrop-blur-[2px]"
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-labelledby="lead-details-heading"
            className="absolute inset-y-0 right-0 flex h-dvh w-full max-w-2xl flex-col bg-[#fbfcfa] shadow-2xl"
          >
            <header className="flex items-start justify-between gap-5 border-b border-line bg-white px-5 py-5 sm:px-7">
              <div className="min-w-0">
                <p className="text-[10px] font-bold uppercase tracking-[.16em] text-forest">
                  {selectedCase ? "Case workspace" : "Lead details"}
                </p>
                <h2
                  id="lead-details-heading"
                  className="mt-1 break-words font-serif text-2xl text-ink sm:text-3xl"
                >
                  {selectedLead.title}
                </h2>
                <p className="mt-2 text-sm text-muted">
                  {selectedLead.category.replaceAll("_", " ")} · {selectedLead.region}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <StatusPill status={selectedCase?.status ?? selectedLead.status} />
                <button
                  type="button"
                  aria-label="Close details"
                  onClick={closeDetails}
                  className="rounded-xl p-2 text-muted transition hover:bg-canvas hover:text-ink"
                >
                  <X size={20} />
                </button>
              </div>
            </header>

            <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5 sm:p-7">
              <Card className="p-5">
                <h3 className="text-sm font-bold text-ink">Details</h3>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-muted">
                  {selectedLead.description}
                </p>
              </Card>

              {selectedCase ? (
                <>
                  <Card className="p-5">
                    <CaseTimeline status={selectedCase.status} />
                  </Card>
                  <DocumentExchange
                    caseRecord={selectedCase}
                    onUploaded={(document) => {
                      const updated = {
                        ...selectedCase,
                        documents: [...selectedCase.documents, document],
                      };
                      setSelectedCase(updated);
                      setCases((current) =>
                        current.map((record) =>
                          record.id === updated.id
                            ? {
                                ...record,
                                document_count: record.document_count + 1,
                              }
                            : record,
                        ),
                      );
                    }}
                  />
                </>
              ) : selectedLead.status === "ACCEPTED" ? (
                <InlineMessage tone="info">
                  This lead was accepted. Its case details are still loading.
                </InlineMessage>
              ) : (
                <Card className="p-5">
                  <h3 className="text-sm font-bold text-ink">Case status</h3>
                  <p className="mt-2 text-sm leading-6 text-muted">
                    Once a legal team accepts this lead, its case and progress will appear here.
                  </p>
                </Card>
              )}
            </div>
          </aside>
        </DrawerPortal>
      )}
    </>
  );
}

function Metric({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: number;
}) {
  return (
    <Card className="flex items-center gap-4 p-4">
      <div className="rounded-xl bg-mint p-2.5 text-forest">{icon}</div>
      <div>
        <p className="text-2xl font-semibold text-ink">{value}</p>
        <p className="text-xs text-muted">{label}</p>
      </div>
    </Card>
  );
}

const caseStages = ["INTAKE", "INVESTIGATION", "DISCOVERY", "SETTLED", "CLOSED"];

function CaseTimeline({ status }: { status: string }) {
  const activeIndex = caseStages.indexOf(status);
  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-ink">Case progress</h3>
          <p className="mt-1 text-xs text-muted">Your team will keep this updated.</p>
        </div>
        <FolderOpen size={17} className="text-muted" />
      </div>
      <ol className="space-y-0">
        {caseStages.map((stage, index) => {
          const complete = index <= activeIndex;
          return (
            <li key={stage} className="relative flex min-h-12 gap-3">
              {index < caseStages.length - 1 && (
                <span
                  className={`absolute left-[9px] top-5 h-7 w-px ${index < activeIndex ? "bg-forest/50" : "bg-line"}`}
                />
              )}
              <span
                className={`relative mt-1 h-[19px] w-[19px] rounded-full border-[5px] ${complete ? "border-mint bg-forest" : "border-line bg-white"}`}
              />
              <span className={`text-sm ${complete ? "font-semibold text-ink" : "text-muted"}`}>
                {stage.charAt(0) + stage.slice(1).toLowerCase()}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
