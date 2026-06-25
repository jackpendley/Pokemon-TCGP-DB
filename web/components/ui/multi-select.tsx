"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

export interface MSOption {
  value: string;
  label: string;
}

/** Quick "select all of these" actions shown above the options (e.g. Series A/B). */
export interface MSGroup {
  label: string;
  values: string[];
}

/**
 * A compact multi-select dropdown: a button that opens a checkbox panel. Nothing
 * selected reads as "All <label>"; selections show a count. Closes on outside click.
 */
export function MultiSelect({
  label,
  options,
  selected,
  onChange,
  groups,
  renderOption,
}: {
  label: string;
  options: MSOption[];
  selected: string[];
  onChange: (values: string[]) => void;
  groups?: MSGroup[];
  renderOption?: (value: string) => string;
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

  const toggle = (v: string) =>
    onChange(
      selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v],
    );

  const count = selected.length;

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
        <div className="absolute z-20 mt-1 max-h-72 w-56 overflow-auto rounded-md border bg-popover p-1 text-popover-foreground shadow-md">
          {(groups?.length || count > 0) && (
            <div className="mb-1 flex flex-wrap gap-1 border-b p-1">
              {groups?.map((g) => (
                <button
                  key={g.label}
                  type="button"
                  onClick={() =>
                    onChange([...new Set([...selected, ...g.values])])
                  }
                  className="rounded bg-muted px-2 py-1 text-xs hover:bg-muted/70"
                >
                  {g.label}
                </button>
              ))}
              {count > 0 ? (
                <button
                  type="button"
                  onClick={() => onChange([])}
                  className="rounded px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  Clear
                </button>
              ) : null}
            </div>
          )}
          {options.map((o) => (
            <label
              key={o.value}
              className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-muted"
            >
              <input
                type="checkbox"
                checked={selected.includes(o.value)}
                onChange={() => toggle(o.value)}
                className="size-3.5 accent-primary"
              />
              <span>{renderOption ? renderOption(o.value) : o.label}</span>
            </label>
          ))}
        </div>
      ) : null}
    </div>
  );
}
