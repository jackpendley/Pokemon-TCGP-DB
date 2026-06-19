"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowDown, ArrowUp, ChevronsUpDown, Info } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { formatEv, formatPercent, packSlug, titleCase } from "@/lib/domain/format";
import type { PackRecord } from "@/types";

type SortKey =
  | "pack_name"
  | "unified_score"
  | "new_card_ev_10x"
  | "copy_ev"
  | "ev_diminishing_returns_ratio"
  | "missing_in_pool"
  | "cost_per_unique_card_10x"
  | "confidence_weight";

interface Column {
  key: SortKey;
  label: string;
  numeric: boolean;
  align: "left" | "right";
  info?: string;
  render: (p: PackRecord) => React.ReactNode;
}

const COLUMNS: Column[] = [
  {
    key: "pack_name",
    label: "Pack",
    numeric: false,
    align: "left",
    render: (p) => (
      <>
        <Link
          href={`/packs/${packSlug(p.pack_name)}`}
          className="font-medium hover:underline"
        >
          {p.pack_name}
        </Link>
        <div className="text-xs text-muted-foreground">
          {p.expansion} · {p.set_code}
        </div>
      </>
    ),
  },
  {
    key: "unified_score",
    label: "Unified",
    numeric: true,
    align: "right",
    render: (p) => <span className="font-medium">{formatEv(p.unified_score)}</span>,
  },
  {
    key: "new_card_ev_10x",
    label: "New-card EV (10×)",
    numeric: true,
    align: "right",
    render: (p) => formatEv(p.new_card_ev_10x),
  },
  {
    key: "copy_ev",
    label: "Copy EV",
    numeric: true,
    align: "right",
    render: (p) => formatEv(p.copy_ev),
  },
  {
    key: "ev_diminishing_returns_ratio",
    label: "DR",
    numeric: true,
    align: "right",
    info: "Diminishing returns: how well a 10-pack holds its value versus single packs. Lower means the pool is near-complete, so returns drop off — consider switching packs.",
    render: (p) => formatPercent(p.ev_diminishing_returns_ratio, 0),
  },
  {
    key: "missing_in_pool",
    label: "Missing",
    numeric: true,
    align: "right",
    render: (p) => `${p.missing_in_pool}/${p.cards_in_pool}`,
  },
  {
    key: "cost_per_unique_card_10x",
    label: "Cost / uniq",
    numeric: true,
    align: "right",
    render: (p) => formatEv(p.cost_per_unique_card_10x),
  },
  {
    key: "confidence_weight",
    label: "Confidence",
    numeric: true,
    align: "left",
    render: (p) => (
      <Badge variant={p.confidence_weight >= 1 ? "secondary" : "outline"}>
        {titleCase(p.slot_rates_confidence)}
      </Badge>
    ),
  },
];

type Series = "all" | "A" | "B";

const SERIES_OPTIONS: { value: Series; label: string }[] = [
  { value: "all", label: "All" },
  { value: "A", label: "A-series" },
  { value: "B", label: "B-series" },
];

export function PacksTable({ packs }: { packs: PackRecord[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("unified_score");
  const [dir, setDir] = useState<"asc" | "desc">("desc");
  const [series, setSeries] = useState<Series>("all");

  const sorted = useMemo(() => {
    const col = COLUMNS.find((c) => c.key === sortKey)!;
    const factor = dir === "asc" ? 1 : -1;
    return [...packs]
      .filter(
        (p) => series === "all" || p.set_code.toUpperCase().startsWith(series),
      )
      .sort((a, b) => {
        if (col.numeric) {
          return ((a[sortKey] as number) - (b[sortKey] as number)) * factor;
        }
        return String(a[sortKey]).localeCompare(String(b[sortKey])) * factor;
      });
  }, [packs, sortKey, dir, series]);

  function toggle(key: SortKey, numeric: boolean) {
    if (key === sortKey) {
      setDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      // Numbers feel natural high→low first; text low→high first.
      setDir(numeric ? "desc" : "asc");
    }
  }

  return (
    <div className="space-y-3">
      <div className="inline-flex rounded-md border p-0.5">
        {SERIES_OPTIONS.map((opt) => (
          <Button
            key={opt.value}
            type="button"
            size="sm"
            variant={series === opt.value ? "secondary" : "ghost"}
            className="h-7"
            onClick={() => setSeries(opt.value)}
          >
            {opt.label}
          </Button>
        ))}
      </div>
      <div className="overflow-x-auto rounded-lg border">
        <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-10">#</TableHead>
            {COLUMNS.map((c) => (
              <TableHead
                key={c.key}
                className={c.align === "right" ? "text-right" : undefined}
              >
                <span
                  className={cn(
                    "inline-flex items-center gap-1",
                    c.align === "right" && "flex-row-reverse",
                  )}
                >
                  <button
                    type="button"
                    onClick={() => toggle(c.key, c.numeric)}
                    className={cn(
                      "inline-flex items-center gap-1 hover:text-foreground",
                      c.align === "right" && "flex-row-reverse",
                      sortKey === c.key
                        ? "text-foreground"
                        : "text-muted-foreground",
                    )}
                  >
                    {c.label}
                    {sortKey === c.key ? (
                      dir === "asc" ? (
                        <ArrowUp className="size-3.5" />
                      ) : (
                        <ArrowDown className="size-3.5" />
                      )
                    ) : (
                      <ChevronsUpDown className="size-3.5 opacity-50" />
                    )}
                  </button>
                  {c.info ? (
                    <Tooltip>
                      <TooltipTrigger
                        className="text-muted-foreground/70 hover:text-foreground"
                        aria-label={`About ${c.label}`}
                      >
                        <Info className="size-3.5" />
                      </TooltipTrigger>
                      <TooltipContent>{c.info}</TooltipContent>
                    </Tooltip>
                  ) : null}
                </span>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((p, i) => (
            <TableRow key={`${p.set_code}-${p.pack_name}`}>
              <TableCell className="tabular-nums text-muted-foreground">
                {i + 1}
              </TableCell>
              {COLUMNS.map((c) => (
                <TableCell
                  key={c.key}
                  className={cn(
                    c.align === "right" && "text-right tabular-nums",
                  )}
                >
                  {c.render(p)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
        </Table>
      </div>
    </div>
  );
}
