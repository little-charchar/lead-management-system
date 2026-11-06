"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui";

export function Pagination({
  page,
  pageSize,
  total,
  label,
  onPageChange,
  disabled = false,
  borderTop = true,
}: {
  page: number;
  pageSize: number;
  total: number;
  label: string;
  onPageChange: (page: number) => void;
  disabled?: boolean;
  borderTop?: boolean;
}) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const [pageInput, setPageInput] = useState(String(currentPage + 1));

  useEffect(() => {
    if (page !== currentPage) onPageChange(currentPage);
  }, [currentPage, onPageChange, page]);

  useEffect(() => {
    setPageInput(String(currentPage + 1));
  }, [currentPage]);

  function navigateToPage() {
    const requestedPage = Number(pageInput);
    if (!Number.isInteger(requestedPage)) {
      setPageInput(String(currentPage + 1));
      return;
    }
    const nextPage = Math.min(pageCount, Math.max(1, requestedPage));
    setPageInput(String(nextPage));
    onPageChange(nextPage - 1);
  }

  return (
    <div className={`flex flex-wrap items-center justify-between gap-3 px-5 py-3 sm:px-6 ${borderTop ? "border-t border-line" : ""}`}>
      <Button
        type="button"
        variant="secondary"
        className="px-3 py-2"
        disabled={disabled || currentPage === 0}
        aria-label={`Previous ${label}`}
        onClick={() => onPageChange(Math.max(0, currentPage - 1))}
      >
        <ChevronLeft size={17} /> Previous
      </Button>
      <div className="flex items-center justify-center gap-2 text-xs text-muted">
        <label htmlFor={`pagination-page-${label}`}>
          Page
        </label>
        <input
          type="number"
          min={1}
          max={pageCount}
          step={1}
          id={`pagination-page-${label}`}
          value={pageInput}
          disabled={disabled || total === 0}
          onChange={(event) => setPageInput(event.target.value)}
          onBlur={navigateToPage}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.currentTarget.blur();
            }
          }}
          className="field-input w-16 px-2 py-2 text-center"
          aria-label={`Page number for ${label}`}
        />
        <span>
          of {pageCount} · {total} {label}
        </span>
      </div>
      <Button
        type="button"
        variant="secondary"
        className="px-3 py-2"
        disabled={disabled || currentPage >= pageCount - 1}
        aria-label={`Next ${label}`}
        onClick={() => onPageChange(Math.min(pageCount - 1, currentPage + 1))}
      >
        Next <ChevronRight size={17} />
      </Button>
    </div>
  );
}
