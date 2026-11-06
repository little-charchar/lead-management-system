"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import {
  Check,
  LockKeyhole,
  Search,
  Send,
  X,
} from "lucide-react";

import {
  api,
  type ApiError,
  type CaseRecord,
  type CaseListRecord,
  type CaseStatus,
  type PrivateNote,
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

const stages: CaseStatus[] = [
  "INTAKE",
  "INVESTIGATION",
  "DISCOVERY",
  "SETTLED",
  "CLOSED",
];
const statusFilters = ["ALL", ...stages] as const;
type CaseStatusFilter = (typeof statusFilters)[number];
const PAGE_SIZE = 10;

export function CaseWorkspace({
  initialCase,
}: {
  initialCase: CaseRecord | null;
}) {
  const [cases, setCases] = useState<CaseListRecord[]>([]);
  const [record, setRecord] = useState<CaseRecord | null>(initialCase);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<CaseStatusFilter>("ALL");
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [busy, setBusy] = useState(true);
  const [statusBusy, setStatusBusy] = useState(false);
  const [noteBusy, setNoteBusy] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const requestId = useRef(0);

  const loadCases = useCallback(async () => {
    const currentRequestId = ++requestId.current;
    setError("");
    try {
      const results = await api.fetchFirmCasePage({
        search: search.trim().length >= 2 ? search.trim() : undefined,
        status: stages.includes(statusFilter as CaseStatus)
          ? (statusFilter as CaseStatus)
          : undefined,
        include_closed: statusFilter === "ALL",
        offset: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      });
      if (currentRequestId !== requestId.current) return;
      setCases(results.items);
      setTotal(results.total);
    } catch (reason) {
      if (currentRequestId !== requestId.current) return;
      setError((reason as ApiError).message ?? "Cases could not be loaded.");
    } finally {
      if (currentRequestId === requestId.current) setBusy(false);
    }
  }, [initialCase, page, search, statusFilter]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadCases(), 0);
    return () => window.clearTimeout(timer);
  }, [loadCases]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setPage(0);
      setSearch(searchInput.trim());
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    if (!record) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setRecord(null);
    };
    document.addEventListener("keydown", closeOnEscape);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.body.style.overflow = "";
    };
  }, [record]);

  async function changeStatus(value: CaseStatus) {
    if (!record) return;
    setStatusBusy(true);
    setError("");
    try {
      const updated = await api.updateCaseStatus(record.id, value);
      setRecord(updated);
      setCases((current) =>
        current.map((item) =>
          item.id === updated.id
            ? { ...item, status: updated.status, updated_at: updated.updated_at }
            : item,
        ),
      );
      setNotice("Case progress updated.");
      void loadCases();
    } catch (reason) {
      setError((reason as ApiError).message ?? "The status could not be updated.");
    } finally {
      setStatusBusy(false);
    }
  }

  async function addNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!record || !noteText.trim()) return;
    setNoteBusy(true);
    setError("");
    try {
      const note: PrivateNote = await api.createNote(record.id, noteText.trim());
      setRecord((current) =>
        current ? { ...current, notes: [...(current.notes ?? []), note] } : current,
      );
      setNoteText("");
      setNotice("Private note added to this firm’s case file.");
    } catch (reason) {
      setError((reason as ApiError).message ?? "The note could not be saved.");
    } finally {
      setNoteBusy(false);
    }
  }

  async function openCase(item: CaseListRecord) {
    setRecord(null);
    setError("");
    setNotice("");
    setNoteText("");
    try {
      setRecord(await api.fetchCase(item.id));
    } catch (reason) {
      setError((reason as ApiError).message ?? "Case details could not be loaded.");
    }
  }

  function closeCase() {
    setRecord(null);
    setError("");
    setNotice("");
  }

  return (
    <div className="space-y-5">
      <Card className="overflow-hidden">
        <div className="flex flex-wrap items-end justify-between gap-4 border-b border-line p-5 sm:px-6">
          <div>
            <h3 className="font-serif text-xl text-ink">Cases assigned to your firm</h3>
            <p className="mt-1 text-xs text-muted">
              Search by client, email, title, category, or region and filter by status.
            </p>
          </div>
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
            <label className="relative min-w-[220px] flex-1 sm:w-80">
              <span className="sr-only">Search active cases</span>
              <Search
                size={15}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
              />
              <input
                value={searchInput}
                onChange={(event) => {
                  setSearchInput(event.target.value);
                  setPage(0);
                }}
                placeholder="Name, email, title, category, region…"
                className="field-input pl-9"
              />
            </label>
            <select
              value={statusFilter}
              onChange={(event) => {
                setStatusFilter(event.target.value as CaseStatusFilter);
                setPage(0);
              }}
              className="field-input w-auto min-w-[190px]"
              aria-label="Filter cases by status"
            >
              <option value="ALL">All statuses</option>
              {stages.map((stage) => (
                <option key={stage} value={stage}>{stage.replaceAll("_", " ")}</option>
              ))}
            </select>
          </div>
        </div>

        {error && <div className="p-5 pb-0"><InlineMessage tone="error">{error}</InlineMessage></div>}
        {busy ? (
          <p className="p-8 text-center text-sm text-muted">Loading assigned cases…</p>
        ) : cases.length === 0 ? (
          <EmptyState
            icon={<Search size={21} />}
            title={search || statusFilter !== "ALL" ? "No matching cases" : "No cases yet"}
            description={
              search
                ? "Try another name, email, title, category, or region."
                : "Cases accepted by your firm will appear here."
            }
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[700px] text-left">
                <thead className="bg-canvas/70 text-[10px] uppercase tracking-wider text-muted">
                  <tr>
                    <th className="px-5 py-3 font-semibold sm:px-6">Case</th>
                    <th className="px-5 py-3 font-semibold">Client</th>
                    <th className="px-5 py-3 font-semibold">Category / region</th>
                    <th className="px-5 py-3 font-semibold">Status</th>
                    <th className="px-5 py-3 font-semibold">Updated</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {cases.map((item) => (
                    <tr
                      key={item.id}
                      tabIndex={0}
                      onClick={() => openCase(item)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          openCase(item);
                        }
                      }}
                      className={`cursor-pointer transition hover:bg-canvas/70 ${record?.id === item.id ? "bg-mint/30" : ""}`}
                    >
                      <td className="px-5 py-4 sm:px-6">
                        <p className="text-sm font-semibold text-ink">{item.lead.title}</p>
                        <p className="mt-1 text-xs text-muted">Accepted matter</p>
                      </td>
                      <td className="px-5 py-4">
                        <p className="text-sm text-ink">{item.lead.plaintiff?.name ?? "Client"}</p>
                        <p className="mt-1 text-xs text-muted">{item.lead.plaintiff?.email}</p>
                      </td>
                      <td className="px-5 py-4 text-sm text-muted">
                        {item.lead.category.replaceAll("_", " ")} · {item.lead.region}
                      </td>
                      <td className="px-5 py-4"><StatusPill status={item.status} /></td>
                      <td className="px-5 py-4 text-xs text-muted">
                        {new Date(item.updated_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {total > 0 && (
              <Pagination
                page={page}
                pageSize={PAGE_SIZE}
                total={total}
                label="cases"
                disabled={busy}
                onPageChange={setPage}
              />
            )}
          </>
        )}
      </Card>

      {record && (
        <DrawerPortal>
          <button
            type="button"
            aria-label="Close case details"
            onClick={closeCase}
            className="absolute inset-0 h-full w-full bg-ink/45 backdrop-blur-[2px]"
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-labelledby="firm-case-heading"
            className="absolute inset-y-0 right-0 flex h-dvh w-full max-w-2xl flex-col bg-[#fbfcfa] shadow-2xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-line bg-white px-5 py-5 sm:px-7">
              <div className="min-w-0">
                <p className="text-[10px] font-bold uppercase tracking-[.16em] text-forest">
                  {record.lead.plaintiff?.name ?? "Client"}
                </p>
                <h2 id="firm-case-heading" className="mt-1 break-words font-serif text-2xl text-ink sm:text-3xl">
                  {record.lead.title}
                </h2>
                <p className="mt-2 text-sm text-muted">
                  {record.lead.plaintiff?.email}
                </p>
                <p className="mt-1 text-xs text-muted">
                  {record.lead.category.replaceAll("_", " ")} · {record.lead.region}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                <StatusPill status={record.status} />
                <button
                  type="button"
                  aria-label="Close case details"
                  onClick={closeCase}
                  className="rounded-xl p-2 text-muted transition hover:bg-canvas hover:text-ink"
                >
                  <X size={20} />
                </button>
              </div>
            </header>

            <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5 sm:p-7">
              {notice && <InlineMessage tone="success">{notice}</InlineMessage>}
              {error && <InlineMessage tone="error">{error}</InlineMessage>}

              <Card className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-bold text-ink">Case progress</h3>
                    <p className="mt-1 text-xs leading-5 text-muted">
                      Select a stage to update the case.
                    </p>
                  </div>
                  {statusBusy && (
                    <span role="status" className="text-xs font-medium text-forest">
                      Saving progress…
                    </span>
                  )}
                </div>
                <ol className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-5">
                  {stages.map((stage, index) => {
                    const activeIndex = stages.indexOf(record.status);
                    const complete = index < activeIndex;
                    const active = index === activeIndex;
                    return (
                      <li key={stage}>
                        <button
                          type="button"
                          aria-label={`Set case status to ${stage.replaceAll("_", " ")}`}
                          aria-pressed={active}
                          disabled={statusBusy || active}
                          onClick={() => void changeStatus(stage)}
                          className={`flex min-h-[92px] w-full flex-col items-start rounded-xl border p-3 text-left transition ${
                            active
                              ? "border-forest bg-mint/50 text-forest ring-1 ring-forest"
                              : complete
                                ? "border-forest/20 bg-mint/20 text-forest hover:border-forest"
                                : "border-line bg-white text-muted hover:border-forest/50 hover:bg-canvas"
                          } disabled:cursor-default`}
                        >
                          <span
                            className={`grid h-6 w-6 place-items-center rounded-full text-[10px] font-bold ${
                              active
                                ? "bg-forest text-white"
                                : complete
                                  ? "bg-mint text-forest"
                                  : "bg-canvas text-muted"
                            }`}
                          >
                            {complete ? <Check size={14} /> : index + 1}
                          </span>
                          <span className="mt-2 text-xs font-semibold leading-4">
                            {stage.replaceAll("_", " ")}
                          </span>
                          <span className="mt-1 text-[10px] opacity-75">
                            {active ? "Current stage" : complete ? "Completed" : "Set stage"}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ol>
                <p className="mt-3 text-[11px] leading-5 text-muted">
                  Status changes are saved immediately and added to the case audit history.
                </p>
              </Card>

              <Card className="p-5">
                <h3 className="text-sm font-bold text-ink">Case information</h3>
                <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                      Client
                    </dt>
                    <dd className="mt-1 text-ink">
                      {record.lead.plaintiff?.name ?? "Client"}
                    </dd>
                    <dd className="text-xs text-muted">
                      {record.lead.plaintiff?.email}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                      Category and region
                    </dt>
                    <dd className="mt-1 text-ink">
                      {record.lead.category.replaceAll("_", " ")} · {record.lead.region}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted">
                      Last updated
                    </dt>
                    <dd className="mt-1 text-ink">
                      {new Date(record.updated_at).toLocaleString()}
                    </dd>
                  </div>
                </dl>
                <div className="mt-4 border-t border-line pt-4">
                  <h3 className="text-sm font-bold text-ink">Case details</h3>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-muted">
                    {record.lead.description}
                  </p>
                </div>
              </Card>

              <DocumentExchange
                caseRecord={record}
                showCaseRetentionNote={false}
                onUploaded={(document) => {
                  const updated = { ...record, documents: [...record.documents, document] };
                  setRecord(updated);
                  setCases((current) =>
                    current.map((item) =>
                      item.id === updated.id
                        ? { ...item, document_count: item.document_count + 1 }
                        : item,
                    ),
                  );
                }}
              />

              <Card className="p-5 sm:p-6">
                <div className="flex items-center gap-2 text-forest">
                  <LockKeyhole size={17} />
                  <h3 className="text-sm font-bold">Case messages</h3>
                  <span className="rounded-full bg-canvas px-2 py-0.5 text-[10px] text-muted">
                    {record.notes?.length ?? 0}
                  </span>
                </div>
                {record.notes?.length ? (
                  <div className="mt-4 space-y-3">
                    {record.notes.map((note) => (
                      <article key={note.id} className="rounded-xl bg-canvas/70 p-4">
                        <p className="whitespace-pre-wrap text-sm leading-6 text-ink">
                          {note.content}
                        </p>
                        <p className="mt-2 text-[10px] text-muted">
                          {note.author?.name ?? "Former staff"} ·{" "}
                          {new Date(note.created_at).toLocaleString()}
                        </p>
                      </article>
                    ))}
                  </div>
                ) : (
                  <p className="mt-3 text-sm text-muted">No private notes yet.</p>
                )}
                <form onSubmit={addNote} className="mt-4">
                  <label className="field-label">
                    Add a case note
                    <textarea
                      value={noteText}
                      onChange={(event) => setNoteText(event.target.value)}
                      required
                      minLength={1}
                      rows={4}
                      placeholder="Record an internal update…"
                      className="field-input resize-y bg-white"
                    />
                  </label>
                  <Button type="submit" className="mt-3 w-full" disabled={noteBusy}>
                    <Send size={14} />
                    {noteBusy ? "Saving…" : "Save private note"}
                  </Button>
                </form>
              </Card>
            </div>
          </aside>
        </DrawerPortal>
      )}
    </div>
  );
}
