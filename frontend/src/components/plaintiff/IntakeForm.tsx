"use client";

import { useState, type FormEvent } from "react";
import { CheckCircle2, FilePlus2, Paperclip, Send, UserRound } from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { api, type ApiError, type Lead } from "@/lib/api";
import { Button, Card, InlineMessage } from "@/components/ui";

const categories = [
  ["PERSONAL_INJURY", "Personal injury"],
  ["LABOR", "Employment & labor"],
  ["FAMILY", "Family law"],
  ["IMMIGRATION", "Immigration"],
  ["OTHER", "Other"],
];

const regions = [
  ["NY", "New York"],
  ["CA", "California"],
  ["ON", "Ontario"],
  ["TX", "Texas"],
];
const MAX_DESCRIPTION_WORDS = 1000;

function countWords(value: string): number {
  const trimmed = value.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

export function IntakeForm({ onCreated }: { onCreated: (lead: Lead) => void }) {
  const { persona } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [created, setCreated] = useState<Lead | null>(null);
  const [description, setDescription] = useState("");
  const [attachmentError, setAttachmentError] = useState("");
  const [retryLeadId, setRetryLeadId] = useState<number | null>(null);
  const [retryFiles, setRetryFiles] = useState<File[]>([]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setError("");
    setAttachmentError("");
    setCreated(null);
    const form = new FormData(formElement);
    const details = String(form.get("description") ?? "");
    const requiredValues = [
      persona.name,
      persona.email,
      String(form.get("title") ?? ""),
      String(form.get("category") ?? ""),
      String(form.get("region") ?? ""),
      details,
    ];
    if (requiredValues.some((value) => value.trim().length === 0)) {
      setError("Please complete all required fields.");
      return;
    }
    if (countWords(details) > MAX_DESCRIPTION_WORDS) {
      setError(`Details must be ${MAX_DESCRIPTION_WORDS} words or fewer.`);
      return;
    }
    setBusy(true);
    try {
      const lead = await api.submitLead({
        plaintiff_name: persona.name,
        email: persona.email,
        title: String(form.get("title") ?? ""),
        region: String(form.get("region") ?? ""),
        category: String(form.get("category") ?? ""),
        description: details,
      });
      const attachments = form
        .getAll("attachments")
        .filter((value): value is File => value instanceof File && value.size > 0);
      if (attachments.length > 0) {
        await uploadAttachments(lead.id, attachments);
      }
      setCreated(lead);
      onCreated(lead);
      formElement.reset();
      setDescription("");
    } catch (reason) {
      setError((reason as ApiError).message ?? "We could not submit your request.");
    } finally {
      setBusy(false);
    }
  }

  async function uploadAttachments(leadId: number, files: File[]) {
    const results = await Promise.allSettled(
      files.map((file) => api.uploadLeadAttachment(leadId, file)),
    );
    const failed = results.flatMap((result, index) =>
      result.status === "rejected" ? [files[index]] : [],
    );
    setRetryFiles(failed);
    setRetryLeadId(failed.length > 0 ? leadId : null);
    setAttachmentError(
      failed.length > 0
        ? `The lead was submitted, but ${failed.length} PDF attachment${failed.length === 1 ? "" : "s"} could not be uploaded. Retry the failed upload${failed.length === 1 ? "" : "s"} below.`
        : "",
    );
  }

  async function retryAttachments() {
    if (retryLeadId === null || retryFiles.length === 0) return;
    setBusy(true);
    try {
      await uploadAttachments(retryLeadId, retryFiles);
      setError("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="overflow-hidden">
      <div className="border-b border-line bg-[#fbfcfa] px-6 py-5 sm:px-7">
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-mint p-2.5 text-forest">
            <FilePlus2 size={19} />
          </div>
          <div>
            <h3 className="font-serif text-xl text-ink">Tell us what happened</h3>
            <p className="mt-1 text-sm text-muted">
              A few details help us route your lead to the right team.
            </p>
          </div>
        </div>
      </div>
      <form onSubmit={submit} className="space-y-5 p-6 sm:p-7">
        <div className="rounded-2xl border border-line bg-canvas/60 p-4">
          <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-forest">
            <UserRound size={15} />
            Submitting as
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <p className="inline-flex items-center gap-1 text-[11px] text-muted">
                Full name <span aria-hidden="true" className="text-rose">*</span>
              </p>
              <p className="mt-1 text-sm font-semibold text-ink">{persona.name}</p>
            </div>
            <div>
              <p className="inline-flex items-center gap-1 text-[11px] text-muted">
                Email address <span aria-hidden="true" className="text-rose">*</span>
              </p>
              <p className="mt-1 text-sm font-semibold text-ink">{persona.email}</p>
            </div>
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="field-label sm:col-span-2">
            <span>
              Short summary <span aria-hidden="true" className="text-rose">*</span>
            </span>
            <input
              name="title"
              required
              minLength={3}
              maxLength={200}
              placeholder="Briefly summarize your situation"
              className="field-input"
            />
          </label>
          <label className="field-label">
            <span>
              Category <span aria-hidden="true" className="text-rose">*</span>
            </span>
            <select name="category" required defaultValue="" className="field-input">
              <option value="" disabled>
                Select a category
              </option>
              {categories.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="field-label">
            <span>
              Region <span aria-hidden="true" className="text-rose">*</span>
            </span>
            <select name="region" required defaultValue="" className="field-input">
              <option value="" disabled>
                Select a region
              </option>
              {regions.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="field-label">
          <span>
            Details <span aria-hidden="true" className="text-rose">*</span>
          </span>
          <textarea
            name="description"
            required
            minLength={1}
            maxLength={20000}
            rows={5}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Describe what happened, when it happened, and what help you are looking for."
            className="field-input resize-y"
          />
          <p
            className={`mt-1 text-right text-xs ${
              countWords(description) > MAX_DESCRIPTION_WORDS
                ? "text-rose"
                : "text-muted"
            }`}
            aria-live="polite"
          >
            {countWords(description)} / {MAX_DESCRIPTION_WORDS} words
          </p>
        </label>
        <div className="rounded-2xl border border-line bg-canvas/60 p-4">
          <label className="field-label">
            <span className="flex items-center gap-2">
              <Paperclip size={15} />
              Attach supporting PDFs <span className="font-normal text-muted">(optional)</span>
            </span>
            <input
              name="attachments"
              type="file"
              accept="application/pdf,.pdf"
              multiple
              className="field-input file:mr-3 file:rounded-lg file:border-0 file:bg-mint file:px-3 file:py-2 file:text-xs file:font-semibold file:text-forest"
            />
          </label>
          <p className="mt-2 text-xs leading-5 text-muted">
            Add documents that may help the reviewing legal team. Attachments are linked to your
            lead and remain with it if it becomes a case.
          </p>
        </div>
        {error && <InlineMessage tone="error">{error}</InlineMessage>}
        {attachmentError && <InlineMessage tone="error">{attachmentError}</InlineMessage>}
        {retryFiles.length > 0 && (
          <Button type="button" variant="secondary" disabled={busy} onClick={() => void retryAttachments()}>
            {busy ? "Retrying…" : "Retry failed PDF uploads"}
          </Button>
        )}
        {created && (
          <InlineMessage tone="success">
            <span className="inline-flex items-center gap-2">
              <CheckCircle2 size={16} />
              Lead received. Reference #{created.id} ·{" "}
              {created.status.replaceAll("_", " ")}
            </span>
          </InlineMessage>
        )}
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line pt-5">
          <p className="max-w-sm text-xs leading-5 text-muted">
            Your information is only shared with the team reviewing your lead.
          </p>
          <Button type="submit" disabled={busy}>
            {busy ? "Submitting…" : "Submit lead"}
            <Send size={15} />
          </Button>
        </div>
      </form>
    </Card>
  );
}
