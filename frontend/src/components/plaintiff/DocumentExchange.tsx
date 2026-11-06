"use client";

import { useRef, useState, type ChangeEvent } from "react";
import { Download, Eye, FileText, Paperclip, UploadCloud } from "lucide-react";

import {
  api,
  openPdfPreview,
  type ApiError,
  type CaseRecord,
  type DocumentRecord,
} from "@/lib/api";
import { Card, InlineMessage } from "@/components/ui";

export function DocumentExchange({
  caseRecord,
  onUploaded,
}: {
  caseRecord: CaseRecord;
  onUploaded: (document: DocumentRecord) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function upload(file?: File) {
    if (!file) return;
    setError("");
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setError("Choose a PDF file to upload.");
      return;
    }
    setBusy(true);
    try {
      const document = await api.uploadDocument(caseRecord.id, file);
      onUploaded(document);
    } catch (reason) {
      setError((reason as ApiError).message ?? "The upload could not be completed.");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    void upload(event.target.files?.[0]);
  }

  async function download(document: DocumentRecord) {
    setError("");
    try {
      const blob = await api.downloadDocument(caseRecord.id, document.id);
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = document.file_name;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
    } catch (reason) {
      setError((reason as ApiError).message ?? "The file could not be downloaded.");
    }
  }

  async function preview(loadPdf: () => Promise<Blob>) {
    setError("");
    try {
      await openPdfPreview(loadPdf);
    } catch (reason) {
      setError((reason as ApiError).message ?? "The PDF could not be previewed.");
    }
  }

  return (
    <Card className="p-5 sm:p-6">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <h3 className="font-serif text-xl text-ink">Shared documents</h3>
          <p className="mt-1 text-xs text-muted">
            Files stay attached to your case if the firm changes.
          </p>
        </div>
        <span className="rounded-full bg-canvas px-2.5 py-1 text-xs font-semibold text-muted">
          {caseRecord.documents.length} files
        </span>
      </div>

      <div className="divide-y divide-line">
        {caseRecord.documents.map((document) => (
          <div key={document.id} className="flex items-center gap-3 py-3 first:pt-0">
            <div className="rounded-xl bg-mint/70 p-2.5 text-forest">
              <FileText size={17} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-ink">
                {document.file_name}
              </p>
              <p className="mt-1 text-[11px] text-muted">
                {(document.file_size_bytes / 1024).toFixed(0)} KB ·{" "}
                {new Date(document.created_at).toLocaleDateString()}
              </p>
            </div>
            <div className="flex shrink-0">
              <button
                type="button"
                onClick={() =>
                  void preview(() => api.downloadDocument(caseRecord.id, document.id))
                }
                className="rounded-lg p-2 text-forest hover:bg-mint"
                aria-label={`Preview ${document.file_name}`}
              >
                <Eye size={17} />
              </button>
              <button
                type="button"
                onClick={() => void download(document)}
                className="rounded-lg p-2 text-muted hover:bg-canvas hover:text-forest"
                aria-label={`Download ${document.file_name}`}
              >
                <Download size={17} />
              </button>
            </div>
          </div>
        ))}
        {caseRecord.documents.length === 0 && (
          <p className="py-3 text-sm text-muted">No documents have been shared yet.</p>
        )}
      </div>

      {caseRecord.lead.attachments.length > 0 && (
        <div className="mt-5 border-t border-line pt-4">
          <h4 className="text-sm font-semibold text-ink">Original lead attachments</h4>
          <ul className="mt-2 space-y-2">
            {caseRecord.lead.attachments.map((attachment) => (
              <li key={attachment.id} className="flex items-center gap-3 text-sm">
                <FileText size={15} className="shrink-0 text-forest" />
                <span className="min-w-0 flex-1 truncate text-ink">{attachment.file_name}</span>
                <button
                  type="button"
                  onClick={() =>
                    void preview(() =>
                      api.downloadLeadAttachment(caseRecord.lead.id, attachment.id),
                    )
                  }
                  className="rounded-lg p-2 text-forest hover:bg-mint"
                  aria-label={`Preview ${attachment.file_name}`}
                >
                  <Eye size={17} />
                </button>
                <button
                  type="button"
                  onClick={async () => {
                    setError("");
                    try {
                      const blob = await api.downloadLeadAttachment(
                        caseRecord.lead.id,
                        attachment.id,
                      );
                      const url = URL.createObjectURL(blob);
                      const anchor = window.document.createElement("a");
                      anchor.href = url;
                      anchor.download = attachment.file_name;
                      anchor.click();
                      window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
                    } catch (reason) {
                      setError(
                        (reason as ApiError).message ??
                          "The lead attachment could not be downloaded.",
                      );
                    }
                  }}
                  className="rounded-lg p-2 text-muted hover:bg-canvas hover:text-forest"
                  aria-label={`Download ${attachment.file_name}`}
                >
                  <Download size={17} />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <label
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          void upload(event.dataTransfer.files[0]);
        }}
        className={`mt-5 flex cursor-pointer flex-col items-center rounded-xl border border-dashed px-4 py-5 text-center transition ${dragging ? "border-forest bg-mint/50" : "border-[#cfd8d1] bg-[#fbfcfa] hover:bg-canvas"}`}
      >
        <UploadCloud size={21} className="mb-2 text-forest" />
        <span className="text-sm font-semibold text-ink">
          {busy ? "Uploading document…" : "Drop a PDF here or browse"}
        </span>
        <span className="mt-1 text-[11px] text-muted">PDF files only · up to 25 MB</span>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          disabled={busy}
          onChange={onFileChange}
          className="sr-only"
        />
      </label>
      {error && <div className="mt-3"><InlineMessage tone="error">{error}</InlineMessage></div>}
      <div className="mt-3 flex items-center gap-1.5 text-[10px] text-muted">
        <Paperclip size={12} />
        Uploaded files are visible to the case team.
      </div>
    </Card>
  );
}
