"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Check,
  Download,
  Eye,
  Filter,
  Inbox,
  Search,
  X,
} from "lucide-react";

import {
  api,
  openPdfPreview,
  type ApiError,
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
import { Pagination } from "@/components/Pagination";
import { DrawerPortal } from "@/components/DrawerPortal";

const PAGE_SIZE = 10;

export function PendingLeadCards({
  onAccepted,
}: {
  onAccepted: (record: CaseRecord) => void;
}) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [busyLead, setBusyLead] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const results = await api.fetchInboxPage({
        search: search.length >= 2 ? search : undefined,
        offset: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      });
      setLeads(results.items);
      setTotal(results.total);
    } catch (reason) {
      setError((reason as ApiError).message ?? "The review inbox could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setPage(0);
      setSearch(searchInput.trim());
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    if (!selectedLead) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelectedLead(null);
    };
    document.addEventListener("keydown", closeOnEscape);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.body.style.overflow = "";
    };
  }, [selectedLead]);

  async function decide(lead: Lead, decision: "accept" | "decline") {
    setBusyLead(lead.id);
    setNotice("");
    setError("");
    try {
      if (decision === "accept") {
        const caseRecord = await api.acceptLead(lead.id);
        setSelectedLead(null);
        onAccepted(caseRecord);
        setNotice(`Lead #${lead.id} accepted. Case #${caseRecord.id} is ready.`);
      } else {
        await api.declineLead(lead.id);
        setSelectedLead(null);
        setNotice(`Lead #${lead.id} declined and returned for admin resolution.`);
      }
      await reload();
    } catch (reason) {
      setError((reason as ApiError).message ?? `Could not ${decision} this lead.`);
    } finally {
      setBusyLead(null);
    }
  }

  async function downloadAttachment(lead: Lead, attachmentId: number, fileName: string) {
    setError("");
    try {
      const blob = await api.downloadLeadAttachment(lead.id, attachmentId);
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = fileName;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
    } catch (reason) {
      setError((reason as ApiError).message ?? "The lead attachment could not be downloaded.");
    }
  }

  async function previewAttachment(lead: Lead, attachmentId: number) {
    setError("");
    try {
      await openPdfPreview(() => api.downloadLeadAttachment(lead.id, attachmentId));
    } catch (reason) {
      setError((reason as ApiError).message ?? "The lead attachment could not be previewed.");
    }
  }

  return (
    <Card id="inbox" className="overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line p-5 sm:px-6">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-mint p-2.5 text-forest">
            <Inbox size={19} />
          </div>
          <div>
            <h3 className="font-serif text-xl text-ink">Needs your review</h3>
            <p className="mt-1 text-xs text-muted">Search and review pending leads</p>
          </div>
        </div>
        <label className="relative min-w-[220px]">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search name, title, email…"
            className="field-input pl-9"
          />
        </label>
      </div>
      <div className="p-5 sm:p-6">
        {error && <div className="mb-4"><InlineMessage tone="error">{error}</InlineMessage></div>}
        {notice && <div className="mb-4"><InlineMessage tone="success">{notice}</InlineMessage></div>}
        {loading ? (
          <p className="py-8 text-center text-sm text-muted">Loading review queue…</p>
        ) : leads.length === 0 ? (
          <EmptyState
            icon={<Filter size={21} />}
            title={search ? "No matching leads" : "Inbox is clear"}
            description={
              search
                ? "Try a different name, category, region, or phrase."
                : "New leads assigned to your firm will appear here."
            }
          />
        ) : (
          <div className="grid gap-3 xl:grid-cols-2">
            {leads.map((lead) => (
              <article
                key={lead.id}
                className="rounded-2xl border border-line bg-[#fcfdfb] p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-semibold text-ink">
                      {lead.title}
                    </p>
                    <p className="mt-1 truncate text-xs text-muted">
                      {lead.plaintiff?.name ?? `Lead #${lead.id}`} · {lead.plaintiff?.email}
                    </p>
                  </div>
                  <StatusPill status={lead.status} />
                </div>
                <div className="my-4 flex flex-wrap gap-2">
                  <span className="rounded-full bg-canvas px-3 py-1 text-[11px] font-semibold text-ink">
                    {lead.category.replaceAll("_", " ")}
                  </span>
                  <span className="rounded-full bg-canvas px-3 py-1 text-[11px] font-semibold text-muted">
                    {lead.region}
                  </span>
                  <span className="rounded-full bg-canvas px-3 py-1 text-[11px] text-muted">
                    {new Date(lead.created_at).toLocaleDateString()}
                  </span>
                </div>
                <p className="line-clamp-3 text-sm leading-6 text-muted">
                  {lead.description}
                </p>
                <div className="mt-4 border-t border-line pt-3">
                  <Button
                    type="button"
                    variant="secondary"
                    className="w-full"
                    disabled={busyLead !== null}
                    onClick={() => setSelectedLead(lead)}
                  >
                    Review details · {lead.attachments.length}{" "}
                    {lead.attachments.length === 1 ? "file" : "files"}
                  </Button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
      {!loading && total > 0 && (
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          total={total}
          label="leads"
          disabled={loading}
          onPageChange={setPage}
        />
      )}
      {selectedLead && (
        <DrawerPortal>
          <button
            type="button"
            aria-label="Close lead details"
            onClick={() => setSelectedLead(null)}
            className="absolute inset-0 h-full w-full bg-ink/45 backdrop-blur-[2px]"
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-labelledby="review-lead-heading"
            className="absolute inset-y-0 right-0 flex h-dvh w-full max-w-2xl flex-col bg-[#fbfcfa] shadow-2xl"
          >
            <header className="flex items-start justify-between gap-4 border-b border-line bg-white px-5 py-5 sm:px-7">
              <div className="min-w-0">
                <p className="text-[10px] font-bold uppercase tracking-[.16em] text-forest">
                  Lead #{selectedLead.id} · Submitted{" "}
                  {new Date(selectedLead.created_at).toLocaleDateString()}
                </p>
                <h2 id="review-lead-heading" className="mt-1 break-words font-serif text-2xl text-ink sm:text-3xl">
                  {selectedLead.title}
                </h2>
                <p className="mt-2 text-sm text-muted">
                  {selectedLead.category.replaceAll("_", " ")} · {selectedLead.region}
                </p>
              </div>
              <button
                type="button"
                aria-label="Close lead details"
                onClick={() => setSelectedLead(null)}
                className="rounded-xl p-2 text-muted transition hover:bg-canvas hover:text-ink"
              >
                <X size={20} />
              </button>
            </header>
            <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-5 sm:p-7">
              {error && <InlineMessage tone="error">{error}</InlineMessage>}
              {notice && <InlineMessage tone="success">{notice}</InlineMessage>}
              <Card className="p-5">
                <h3 className="text-sm font-bold text-ink">Lead details</h3>
                <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-muted">
                  {selectedLead.description}
                </p>
                <p className="mt-4 border-t border-line pt-3 text-xs text-muted">
                  {selectedLead.plaintiff?.name} · {selectedLead.plaintiff?.email}
                </p>
              </Card>
              <Card className="p-5">
                <h3 className="text-sm font-bold text-ink">
                  Supporting PDFs ({selectedLead.attachments.length})
                </h3>
                {selectedLead.attachments.length === 0 ? (
                  <p className="mt-3 text-sm text-muted">No files were attached to this lead.</p>
                ) : (
                  <ul className="mt-3 space-y-2">
                    {selectedLead.attachments.map((attachment) => (
                      <li key={attachment.id} className="flex items-center gap-2 rounded-xl bg-canvas p-3">
                        <span className="min-w-0 flex-1 truncate text-sm text-ink">
                          {attachment.file_name}
                          <span className="ml-2 text-xs text-muted">
                            ({(attachment.file_size_bytes / 1024).toFixed(0)} KB)
                          </span>
                        </span>
                        <button
                          type="button"
                          onClick={() => void previewAttachment(selectedLead, attachment.id)}
                          aria-label={`Preview ${attachment.file_name}`}
                          className="rounded-lg p-2 text-forest hover:bg-mint"
                        >
                          <Eye size={16} />
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            void downloadAttachment(
                              selectedLead,
                              attachment.id,
                              attachment.file_name,
                            )
                          }
                          aria-label={`Download ${attachment.file_name}`}
                          className="rounded-lg p-2 text-muted hover:bg-white hover:text-forest"
                        >
                          <Download size={16} />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
              <div className="sticky bottom-0 flex gap-3 border-t border-line bg-[#fbfcfa] py-4">
                <Button
                  type="button"
                  className="flex-1"
                  disabled={busyLead !== null}
                  onClick={() => void decide(selectedLead, "accept")}
                >
                  <Check size={15} />
                  {busyLead === selectedLead.id ? "Working…" : "Accept lead"}
                </Button>
                <Button
                  type="button"
                  variant="secondary"
                  disabled={busyLead !== null}
                  onClick={() => void decide(selectedLead, "decline")}
                >
                  <X size={15} /> Decline
                </Button>
              </div>
            </div>
          </aside>
        </DrawerPortal>
      )}
    </Card>
  );
}
