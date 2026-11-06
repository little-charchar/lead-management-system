"use client";

import { useState } from "react";
import { Search } from "lucide-react";

import type { LawFirm } from "@/lib/api";

export function FirmPicker({
  firms,
  selectedFirmId,
  onSelect,
  placeholder = "Search firms…",
  ariaLabel = "Search law firms",
}: {
  firms: LawFirm[];
  selectedFirmId: number | null;
  onSelect: (firm: LawFirm | null) => void;
  placeholder?: string;
  ariaLabel?: string;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const selectedFirm = firms.find((firm) => firm.id === selectedFirmId);
  const matchingFirms = firms.filter((firm) =>
    firm.name.toLowerCase().includes(query.trim().toLowerCase()),
  );
  const inputValue = open ? query : selectedFirm?.name ?? "";

  function choose(firm: LawFirm | null) {
    onSelect(firm);
    setQuery("");
    setOpen(false);
  }

  return (
    <div className="relative min-w-[200px]">
      <label>
        <span className="sr-only">{ariaLabel}</span>
        <Search
          size={15}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
        />
        <input
          value={inputValue}
          onFocus={() => {
            setQuery("");
            setOpen(true);
          }}
          onBlur={() => setOpen(false)}
          onChange={(event) => {
            setQuery(event.target.value);
            onSelect(null);
            setOpen(true);
          }}
          placeholder={placeholder}
          className="field-input pl-9"
          role="combobox"
          aria-expanded={open}
          aria-autocomplete="list"
          autoComplete="off"
        />
      </label>
      {open && (
        <div
          role="listbox"
          aria-label="Matching law firms"
          className="absolute left-0 right-0 top-full z-20 mt-1 max-h-56 overflow-y-auto rounded-xl border border-line bg-white p-1 shadow-xl"
        >
          {matchingFirms.map((firm) => (
            <button
              key={firm.id}
              type="button"
              role="option"
              aria-selected={firm.id === selectedFirmId}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => choose(firm)}
              className="w-full rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-canvas"
            >
              {firm.name}
            </button>
          ))}
          {matchingFirms.length === 0 && (
            <p className="px-3 py-2 text-sm text-muted">No firms match.</p>
          )}
        </div>
      )}
    </div>
  );
}
