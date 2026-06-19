"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
        <div className="text-xs text-muted-foreground">{p.expansion}</div>
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

export function PacksTable({ packs }: { packs: PackRecord[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("unified_score");
  const [dir, setDir] = useState<"asc" | "desc">("desc");

  const sorted = useMemo(() => {
    const col = COLUMNS.find((c) => c.key === sortKey)!;
    const factor = dir === "asc" ? 1 : -1;
    return [...packs].sort((a, b) => {
      if (col.numeric) {
        return ((a[sortKey] as number) - (b[sortKey] as number)) * factor;
      }
      return String(a[sortKey]).localeCompare(String(b[sortKey])) * factor;
    });
  }, [packs, sortKey, dir]);

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
                <button
                  type="button"
                  onClick={() => toggle(c.key, c.numeric)}
                  className={cn(
                    "inline-flex items-center gap-1 hover:text-foreground",
                    c.align === "right" && "flex-row-reverse",
                    sortKey === c.key ? "text-foreground" : "text-muted-foreground",
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
  );
}
