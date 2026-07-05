"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";

import { cn } from "@/lib/utils";

/**
 * Generic multi-select dropdown shell: a button (reads "All <label>" or a count)
 * that opens a panel of arbitrary `children` (the caller lays out the options, e.g.
 * multi-column with icons). Closes on outside click; offers a Clear action.
 */
export function FilterDropdown({
  label,
  count,
  onClear,
  panelClassName,
  children,
}: {
  label: string;
  count: number;
  onClear?: () => void;
  panelClassName?: string;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex h-9 items-center gap-1.5 rounded-md border bg-background px-3 text-sm"
      >
        <span>
          {count > 0 ? `${label} (${count})` : `All ${label.toLowerCase()}`}
        </span>
        <ChevronDown className="size-3.5 text-muted-foreground" />
      </button>

      {open ? (
        <div
          className={cn(
            "absolute z-20 mt-1 max-h-[70vh] overflow-auto rounded-md border bg-popover p-2 text-popover-foreground shadow-md",
            panelClassName,
          )}
        >
          {count > 0 && onClear ? (
            <div className="mb-2 flex justify-end border-b pb-1.5">
              <button
                type="button"
                onClick={onClear}
                className="rounded px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground"
              >
                Clear all
              </button>
            </div>
          ) : null}
          {children}
        </div>
      ) : null}
    </div>
  );
}

/** A checkbox row for a filter option; children render the icon + label. */
export function FilterCheck({
  checked,
  onToggle,
  children,
}: {
  checked: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-muted">
      <input
        type="checkbox"
        checked={checked}
        onChange={onToggle}
        className="size-3.5 shrink-0 accent-primary"
      />
      {children}
    </label>
  );
}
