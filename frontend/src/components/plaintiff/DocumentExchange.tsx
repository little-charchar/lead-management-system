"use client";

import { useMemo, useRef, useState, type ChangeEvent } from "react";
import {
  Download,
  Eye,
  FileText,
  Paperclip,
  Search,
  UploadCloud,
} from "lucide-react";

import {
  api,
  openPdfPreview,
  type ApiError,
  type CaseRecord,
  type DocumentRecord,
  type LeadAttachment,
} from "@/lib/api";
import { Card, InlineMessage } from "@/components/ui";

export function DocumentExchange({
  caseRecord,
  onUploaded,
  allowUpload = true,
  showCaseRetentionNote = true,
  showOriginalLeadAttachments = true,
}: {
  caseRecord: CaseRecord;
  onUploaded?: (document: DocumentRecord) => void;
  allowUpload?: boolean;
  showCaseRetentionNote?: boolean;
  showOriginalLeadAttachments?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [search, setSearch] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const documents = useMemo(
    () =>
      [...caseRecord.documents]
        .sort(
          (left, right) =>
            new Date(right.created_at).getTime() -
              new Date(left.created_at).getTime() ||
            right.id - left.id,
        )
        .filter((document) =>
          matchesSearch(
            search,
            document.file_name,
            document.uploader?.name,
            document.uploader?.law_firm_name,
          ),
        ),
    [caseRecord.documents, search],
  );
  const attachments = useMemo(
    () =>
      [...caseRecord.lead.attachments]
        .sort(
          (left, right) =>
            new Date(right.created_at).getTime() -
              new Date(left.created_at).getTime() ||
            right.id - left.id,
        )
        .filter((attachment) =>
          matchesSearch(
            search,
            attachment.file_name,
            attachment.uploader?.name,
            attachment.uploader?.law_firm_name,
          ),
        ),
    [caseRecord.lead.attachments, search],
  );

  async function upload(file?: File) {
    if (!file || !allowUpload || !onUploaded) return;
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

  async function downloadFile(load: () => Promise<Blob>, fileName: string) {
    setError("");
    try {
      const blob = await load();
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = fileName;
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

  function downloadAttachment(attachment: LeadAttachment) {
    void downloadFile(
      () => api.downloadLeadAttachment(caseRecord.lead.id, attachment.id),
      attachment.file_name,
    );
  }

  return (
    <Card className="p-5 sm:p-6">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div>
          <h3 className="font-serif text-xl text-ink">Shared documents</h3>
          {showCaseRetentionNote && (
            <p className="mt-1 text-xs text-muted">
              Files stay attached to your case if the firm changes.
            </p>
          )}
        </div>
        <span className="rounded-full bg-canvas px-2.5 py-1 text-xs font-semibold text-muted">
          {caseRecord.documents.length + caseRecord.lead.attachments.length} files
        </span>
      </div>

      {allowUpload && (
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
          className={`mb-4 flex cursor-pointer flex-col items-center rounded-xl border border-dashed px-4 py-5 text-center transition ${dragging ? "border-forest bg-mint/50" : "border-[#cfd8d1] bg-[#fbfcfa] hover:bg-canvas"}`}
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
      )}

      <label className="relative mb-4 block">
        <span className="sr-only">Search shared documents</span>
        <Search
          size={15}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
        />
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search documents or uploader…"
          className="field-input pl-9"
        />
      </label>

      <div className="divide-y divide-line">
        {documents.map((document) => (
          <DocumentRow
            key={`document-${document.id}`}
            fileName={document.file_name}
            size={document.file_size_bytes}
            createdAt={document.created_at}
            uploader={uploaderLabel(document.uploader)}
            onPreview={() =>
              preview(() => api.downloadDocument(caseRecord.id, document.id))
            }
            onDownload={() =>
              void downloadFile(
                () => api.downloadDocument(caseRecord.id, document.id),
                document.file_name,
              )
            }
          />
        ))}
        {documents.length === 0 && caseRecord.documents.length > 0 && (
          <p className="py-3 text-sm text-muted">
            No shared documents match “{search}”.
          </p>
        )}
        {caseRecord.documents.length === 0 &&
          attachments.length === 0 &&
          !search && (
          <p className="py-3 text-sm text-muted">No documents have been shared yet.</p>
        )}
        {search && documents.length === 0 && attachments.length === 0 && (
          <p className="py-3 text-sm text-muted">
            No documents match “{search}”.
          </p>
        )}
      </div>

      {showOriginalLeadAttachments &&
        (attachments.length > 0 || caseRecord.lead.attachments.length > 0) && (
        <div className="mt-5 border-t border-line pt-4">
          <h4 className="text-sm font-semibold text-ink">Original lead attachments</h4>
          <ul className="mt-2 divide-y divide-line">
            {attachments.map((attachment) => (
              <li key={attachment.id}>
                <DocumentRow
                  fileName={attachment.file_name}
                  size={attachment.file_size_bytes}
                  createdAt={attachment.created_at}
                  uploader={uploaderLabel(attachment.uploader)}
                  onPreview={() =>
                    preview(() =>
                      api.downloadLeadAttachment(caseRecord.lead.id, attachment.id),
                    )
                  }
                  onDownload={() => void downloadAttachment(attachment)}
                />
              </li>
            ))}
            {attachments.length === 0 && (
              <li className="py-3 text-sm text-muted">
                No original attachments match “{search}”.
              </li>
            )}
          </ul>
        </div>
      )}
      {error && <div className="mt-3"><InlineMessage tone="error">{error}</InlineMessage></div>}
      {allowUpload && (
        <div className="mt-3 flex items-center gap-1.5 text-[10px] text-muted">
          <Paperclip size={12} />
          Uploaded files are visible to the case team.
        </div>
      )}
    </Card>
  );
}

function DocumentRow({
  fileName,
  size,
  createdAt,
  uploader,
  onPreview,
  onDownload,
}: {
  fileName: string;
  size: number;
  createdAt: string;
  uploader: string;
  onPreview: () => void;
  onDownload: () => void;
}) {
  return (
    <div className="flex items-center gap-3 py-3">
      <div className="rounded-xl bg-mint/70 p-2.5 text-forest">
        <FileText size={17} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-ink">{fileName}</p>
        <p className="mt-1 text-[11px] text-muted">
          {uploader} · {(size / 1024).toFixed(0)} KB ·{" "}
          {new Date(createdAt).toLocaleString()}
        </p>
      </div>
      <div className="flex shrink-0">
        <button
          type="button"
          onClick={onPreview}
          className="rounded-lg p-2 text-forest hover:bg-mint"
          aria-label={`Preview ${fileName}`}
        >
          <Eye size={17} />
        </button>
        <button
          type="button"
          onClick={onDownload}
          className="rounded-lg p-2 text-muted hover:bg-canvas hover:text-forest"
          aria-label={`Download ${fileName}`}
        >
          <Download size={17} />
        </button>
      </div>
    </div>
  );
}

function uploaderLabel(
  uploader: DocumentRecord["uploader"] | LeadAttachment["uploader"],
): string {
  if (!uploader) return "Uploader unavailable";
  if (uploader.role === "PLAINTIFF") return `${uploader.name} · Plaintiff`;
  if (uploader.role === "ATTORNEY" || uploader.role === "PARALEGAL") {
    return `${uploader.name} · ${uploader.law_firm_name ?? "Legal team"}`;
  }
  return `${uploader.name} · System administrator`;
}

function matchesSearch(
  query: string,
  ...values: Array<string | null | undefined>
): boolean {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  return (
    normalizedQuery.length === 0 ||
    values.some((value) => value?.toLocaleLowerCase().includes(normalizedQuery))
  );
}
