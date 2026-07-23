import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatNumber } from "@/lib/domain/format";

interface LastRun {
  finishedAt: string | null;
  outcome: string | null;
  mode: string | null;
}

export interface OwnerStatusCardProps {
  publishedAt: string | null;
  lastRun: LastRun | null;
  counts: {
    cards: number;
    packs: number;
    uniqueEntries: number;
    totalQuantity: number;
  };
}

const fmtTime = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString() : "—";

/** Maps a sync outcome to a badge look; unknown/absent → neutral. */
function OutcomeBadge({ outcome }: { outcome: string | null }) {
  if (!outcome) return <Badge variant="outline">no runs yet</Badge>;
  const variant =
    outcome === "ok"
      ? "secondary"
      : outcome === "auth_expired"
        ? "destructive"
        : "outline";
  return <Badge variant={variant}>{outcome}</Badge>;
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-0.5">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="text-sm font-medium tabular-nums">{children}</div>
    </div>
  );
}

/**
 * Owner-only operator panel (Phase 2). Surfaces the sync/publish state and
 * data-integrity counts already in Postgres so the owner can spot a stale or
 * truncated publish at a glance. Rendered only for the authenticated owner;
 * anonymous visitors never receive it.
 */
export function OwnerStatusCard({
  publishedAt,
  lastRun,
  counts,
}: OwnerStatusCardProps) {
  return (
    <Card className="border-primary/30">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <span>Owner · data status</span>
          <Badge variant="ghost" className="text-muted-foreground">
            you
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Field label="Last publish">{fmtTime(publishedAt)}</Field>
          <Field label="Last sync">
            <span className="flex items-center gap-2">
              <OutcomeBadge outcome={lastRun?.outcome ?? null} />
              {lastRun?.mode ? (
                <span className="text-xs text-muted-foreground">
                  {lastRun.mode}
                </span>
              ) : null}
            </span>
          </Field>
          <Field label="Sync finished">{fmtTime(lastRun?.finishedAt ?? null)}</Field>
          <Field label="Cards">{formatNumber(counts.cards)}</Field>
          <Field label="Packs">{formatNumber(counts.packs)}</Field>
          <Field label="Unique / total">
            {formatNumber(counts.uniqueEntries)} /{" "}
            {formatNumber(counts.totalQuantity)}
          </Field>
        </div>
      </CardContent>
    </Card>
  );
}
