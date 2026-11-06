"use client";

import { useEffect, useState } from "react";
import { Activity, ChevronDown, Clock3, FileSearch, UserRound } from "lucide-react";

import { api, type ApiError, type AuditLog, type CaseRecord, type Lead } from "@/lib/api";
import { Button, Card, InlineMessage, StatusPill } from "@/components/ui";

export function AuditInspector({
  entity,
  leadRecord,
  onClose,
}: {
  entity: { type: "LEAD" | "CASE"; id: number } | null;
  leadRecord?: Lead | null;
  onClose: () => void;
}) {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [caseRecord, setCaseRecord] = useState<CaseRecord | null>(null);
  const [lead, setLead] = useState<Lead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const chronologicalLogs = [...logs].sort((a, b) => {
    const timeDifference =
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
    return timeDifference || a.id - b.id;
  });

  useEffect(() => {
    if (!entity) return;
    let active = true;
    Promise.all([
      api.fetchAuditLogs(entity.type, entity.id),
      entity.type === "CASE" ? api.fetchCase(entity.id) : Promise.resolve(null),
    ])
      .then(([audit, matter]) => {
        if (!active) return;
        setLogs(audit);
        setCaseRecord(matter);
        setLead(entity.type === "LEAD" ? (leadRecord ?? null) : null);
      })
      .catch((reason: unknown) => {
        if (active) setError((reason as ApiError).message ?? "Could not load the audit trail.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [entity, leadRecord]);

  if (!entity) return null;

  return (
    <div className="fixed inset-0 z-[65] flex justify-end bg-[#10231f99]" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <aside role="dialog" aria-modal="true" aria-label="Audit trail inspector" className="h-full w-full max-w-2xl overflow-y-auto bg-canvas shadow-2xl">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-white/95 px-6 py-5 backdrop-blur">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[.16em] text-forest">Immutable history</p>
            <h2 className="mt-1 font-serif text-2xl text-ink">
              {entity.type === "CASE" ? "Case" : "Lead"} #{entity.id}
            </h2>
          </div>
          <Button type="button" variant="secondary" onClick={onClose}>Close</Button>
        </div>

        <div className="space-y-5 p-5 sm:p-6">
          {error && <InlineMessage tone="error">{error}</InlineMessage>}
          {entity.type === "CASE" && caseRecord && (
            <Card className="p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[.14em] text-muted">Current case status</p>
                  <p className="mt-1 font-serif text-xl text-ink">
                    {caseRecord.lead.category.replaceAll("_", " ")}
                  </p>
                </div>
                <StatusPill status={caseRecord.status} />
              </div>
              <div className="mt-4 border-t border-line pt-4">
                <p className="mb-3 text-xs font-bold text-ink">Historical private notes · all firms</p>
                {caseRecord.notes?.length ? caseRecord.notes.map((note) => (
                  <div key={note.id} className="mb-2 rounded-xl bg-[#f7f8f6] p-3">
                    <p className="whitespace-pre-wrap text-sm leading-5 text-ink">{note.content}</p>
                    <p className="mt-2 text-[10px] text-muted">
                      {note.author?.name ?? "Former staff"} · Firm #{note.author_firm_id} · {new Date(note.created_at).toLocaleString()}
                    </p>
                  </div>
                )) : <p className="text-xs text-muted">No historical notes.</p>}
              </div>
            </Card>
          )}
          {entity.type === "LEAD" && lead && (
            <Card className="flex items-center justify-between gap-3 p-5">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[.14em] text-muted">Lead record</p>
                <p className="mt-1 font-semibold text-ink">{lead.plaintiff?.name}</p>
                <p className="mt-1 text-xs text-muted">{lead.category.replaceAll("_", " ")} · {lead.region}</p>
              </div>
              <StatusPill status={lead.status} />
            </Card>
          )}
          <div>
            <h3 className="mb-4 flex items-center gap-2 text-sm font-bold text-ink">
              <Activity size={16} className="text-forest" />
              Event timeline
            </h3>
            {loading ? (
              <Card className="p-6 text-center text-sm text-muted">Loading audit history…</Card>
            ) : logs.length === 0 ? (
              <Card className="p-6 text-center text-sm text-muted">No audit entries found.</Card>
            ) : (
              <ol className="relative space-y-4 before:absolute before:bottom-5 before:left-[19px] before:top-5 before:w-px before:bg-line">
                {chronologicalLogs.map((log) => {
                  const date = new Date(log.created_at);
                  const changes = describeChanges(
                    log.previous_state,
                    log.new_state,
                  );
                  return (
                    <li key={log.id} className="relative pl-12">
                      <div className="absolute left-0 top-1 grid h-10 w-10 place-items-center rounded-full border-4 border-canvas bg-mint text-forest">
                        <FileSearch size={15} />
                      </div>
                      <Card className="p-4 sm:p-5">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="text-sm font-bold text-ink">
                              {formatAction(log.action)}
                            </p>
                            <p className="mt-1 flex items-center gap-1.5 text-xs text-muted">
                              <UserRound size={13} />
                              {log.actor?.name ?? "System"} · {log.entity_type} #{log.entity_id}
                            </p>
                          </div>
                          <time
                            dateTime={log.created_at}
                            className="min-w-[155px] text-left sm:text-right"
                          >
                            <span className="block text-sm font-semibold text-ink">
                              {date.toLocaleDateString(undefined, {
                                month: "short",
                                day: "numeric",
                                year: "numeric",
                              })}
                            </span>
                            <span className="mt-0.5 inline-flex items-center gap-1 text-xs text-muted">
                              <Clock3 size={12} />
                              {date.toLocaleTimeString(undefined, {
                                hour: "numeric",
                                minute: "2-digit",
                              })}
                            </span>
                          </time>
                        </div>

                        {changes.length > 0 && (
                          <div className="mt-3 flex flex-wrap gap-2">
                            {changes.map((change) => (
                              <span
                                key={change.label}
                                className="rounded-lg bg-canvas px-3 py-1.5 text-xs text-ink"
                              >
                                <span className="font-medium text-muted">{change.label}: </span>
                                {change.previous} <span className="px-1 text-forest">→</span>
                                <span className="font-semibold">{change.next}</span>
                              </span>
                            ))}
                          </div>
                        )}

                        <details className="group mt-3 border-t border-line pt-3">
                          <summary className="flex cursor-pointer list-none items-center gap-2 text-xs font-semibold text-forest marker:hidden">
                            <ChevronDown
                              size={14}
                              className="transition group-open:rotate-180"
                            />
                            View change details
                          </summary>
                          <div className="mt-3 grid gap-3 sm:grid-cols-2">
                            <StateBlock label="Previous" value={log.previous_state} />
                            <StateBlock label="Updated" value={log.new_state} />
                          </div>
                        </details>
                      </Card>
                    </li>
                  );
                })}
              </ol>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}

function StateBlock({
  label,
  value,
}: {
  label: string;
  value: Record<string, unknown> | null;
}) {
  return (
    <div className="min-w-0 rounded-xl bg-[#f6f7f5] p-3">
      <p className="mb-2 text-[9px] font-bold uppercase tracking-[.13em] text-muted">{label}</p>
      <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-[11px] leading-5 text-[#40504a]">
        {JSON.stringify(value, null, 2) ?? "null"}
      </pre>
    </div>
  );
}

function formatAction(action: string): string {
  const labels: Record<string, string> = {
    AUTO_ROUTED: "Lead submitted",
    ACCEPTED: "Lead accepted",
    DECLINED: "Lead declined",
    REASSIGNED: "Assignment changed",
    STATUS_CHANGED: "Case status updated",
  };
  return labels[action] ?? action.replaceAll("_", " ");
}

function describeChanges(
  previous: Record<string, unknown> | null,
  next: Record<string, unknown>,
): { label: string; previous: string; next: string }[] {
  const labels: Record<string, string> = {
    assigned_firm_id: "Assigned firm",
    case_assigned_firm_id: "Case firm",
    lead_assigned_firm_id: "Lead firm",
    status: "Status",
  };

  return Object.entries(next)
    .filter(([key, value]) => previous?.[key] !== value)
    .map(([key, value]) => ({
      label: labels[key] ?? key.replaceAll("_", " "),
      previous: formatValue(previous?.[key]),
      next: formatValue(value),
    }));
}

function formatValue(value: unknown): string {
  if (value === undefined || value === null) return "None";
  if (typeof value === "string") return value.replaceAll("_", " ");
  if (typeof value === "number") return `Firm #${value}`;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}
