"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { AlertTriangle, ArrowRightLeft, X } from "lucide-react";

import { api, type ApiError, type CaseRecord, type LawFirm, type Lead } from "@/lib/api";
import { Button, InlineMessage } from "@/components/ui";
import { FirmPicker } from "@/components/admin/FirmPicker";

export function ReassignmentDialog({
  lead,
  firms,
  onClose,
  onComplete,
}: {
  lead: Lead | null;
  firms: LawFirm[];
  onClose: () => void;
  onComplete: () => void;
}) {
  const [targetId, setTargetId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!lead || !mounted) return null;
  const selectedLead = lead;

  async function submit() {
    if (!targetId) return;
    setBusy(true);
    setError("");
    try {
      await api.reassignLead(selectedLead.id, Number(targetId));
      onComplete();
      onClose();
    } catch (reason) {
      setError((reason as ApiError).message ?? "The lead could not be reassigned.");
    } finally {
      setBusy(false);
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-[70] flex h-dvh w-screen items-center justify-center overflow-y-auto bg-[#10231fcc] p-4 backdrop-blur-sm">
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="reassign-lead-title"
        className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl sm:p-8"
      >
        <div className="flex items-start justify-between">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-[#fff3df] text-amber">
            <ArrowRightLeft size={20} />
          </div>
          <button type="button" onClick={onClose} aria-label="Close dialog" className="rounded-lg p-2 text-muted hover:bg-canvas">
            <X size={18} />
          </button>
        </div>
        <p className="mt-5 text-[10px] font-bold uppercase tracking-[.16em] text-forest">
          {lead.title} · {lead.status.replaceAll("_", " ")}
        </p>
        <h2 id="reassign-lead-title" className="mt-2 font-serif text-2xl text-ink">
          {lead.status === "PENDING_REVIEW" ? "Reassign lead" : "Assign to a firm"}
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          {lead.status === "PENDING_REVIEW" && lead.assigned_firm
            ? `${lead.assigned_firm.name} will lose access. The selected firm will receive the lead in its pending review inbox.`
            : "The selected team will receive this lead in its pending review inbox."}
        </p>
        {error && <div className="mt-4"><InlineMessage tone="error">{error}</InlineMessage></div>}
        <div className="field-label mt-5">
          <span>Destination law firm</span>
          <div className="mt-2">
            <FirmPicker
              firms={firms}
              selectedFirmId={targetId ? Number(targetId) : null}
              ariaLabel="Search destination law firms"
              onSelect={(firm) => setTargetId(firm ? String(firm.id) : "")}
            />
          </div>
        </div>
        <div className="mt-7 flex justify-end gap-2">
          <Button variant="secondary" type="button" onClick={onClose}>Cancel</Button>
          <Button type="button" disabled={!targetId || busy} onClick={() => void submit()}>
            {busy ? "Assigning…" : "Confirm assignment"}
          </Button>
        </div>
      </section>
    </div>,
    document.body,
  );
}

export function CaseReassignmentDialog({
  caseRecord,
  firms,
  onClose,
  onComplete,
}: {
  caseRecord: CaseRecord | null;
  firms: LawFirm[];
  onClose: () => void;
  onComplete: () => void;
}) {
  const [targetId, setTargetId] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  if (!caseRecord || !mounted) return null;
  const selectedCase = caseRecord;
  const currentFirm = firms.find((firm) => firm.id === selectedCase.assigned_firm_id);
  const targetFirm = firms.find((firm) => firm.id === Number(targetId));

  async function submit() {
    if (!targetId || !confirmed) return;
    setBusy(true);
    setError("");
    try {
      await api.reassignCase(selectedCase.id, Number(targetId));
      onComplete();
      onClose();
    } catch (reason) {
      setError((reason as ApiError).message ?? "The case could not be reassigned.");
    } finally {
      setBusy(false);
    }
  }

  return createPortal(
    <div className="fixed inset-0 z-[70] flex h-dvh w-screen items-center justify-center overflow-y-auto bg-[#10231fcc] p-4 backdrop-blur-sm">
      <section role="dialog" aria-modal="true" aria-labelledby="reassign-case-title" className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl sm:p-8">
        <div className="grid h-11 w-11 place-items-center rounded-2xl bg-rose-50 text-rose">
          <AlertTriangle size={20} />
        </div>
        <p className="mt-5 text-[10px] font-bold uppercase tracking-[.16em] text-rose">
          Access change · {caseRecord.lead.title}
        </p>
        <h2 id="reassign-case-title" className="mt-2 font-serif text-2xl text-ink">Transfer case ownership</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Reassignment immediately revokes {currentFirm?.name ?? "the current firm"} staff access.
          Historical private notes remain visible to administrators and are not shared with the new firm.
        </p>
        {error && <div className="mt-4"><InlineMessage tone="error">{error}</InlineMessage></div>}
        <label className="field-label mt-5">
          New responsible firm
          <div className="mt-2">
            <FirmPicker
              firms={firms.filter((firm) => firm.id !== selectedCase.assigned_firm_id)}
              selectedFirmId={targetId ? Number(targetId) : null}
              ariaLabel="Search new responsible firms"
              onSelect={(firm) => {
                setTargetId(firm ? String(firm.id) : "");
                setConfirmed(false);
              }}
            />
          </div>
        </label>
        {targetFirm && (
          <label className="mt-5 flex cursor-pointer gap-3 rounded-xl border border-rose-100 bg-rose-50/60 p-4 text-sm leading-5 text-rose-900">
            <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} className="mt-1 accent-[#a84d4d]" />
            <span>
              I confirm transferring this matter from <strong>{currentFirm?.name ?? "the current firm"}</strong> to <strong>{targetFirm.name}</strong>, revoking the prior team&apos;s access.
            </span>
          </label>
        )}
        <div className="mt-7 flex justify-end gap-2">
          <Button variant="secondary" type="button" onClick={onClose}>Cancel</Button>
          <Button variant="danger" type="button" disabled={!targetId || !confirmed || busy} onClick={() => void submit()}>
            {busy ? "Transferring…" : "Transfer case"}
          </Button>
        </div>
      </section>
    </div>,
    document.body,
  );
}
