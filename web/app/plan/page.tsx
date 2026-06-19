import { StatCard } from "@/components/dashboard/stat-card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { dataSource } from "@/lib/data";
import { formatEv, formatNumber } from "@/lib/domain/format";

export const dynamic = "force-dynamic";
export const metadata = { title: "Spending Plan · TCGP Optimizer" };

export default async function PlanPage() {
  const doc = await dataSource.getSpendingPlan();
  const plan = doc.spending_plan;

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Hourglass Spending Plan
        </h1>
        <p className="text-sm text-muted-foreground">{plan.description}</p>
      </header>

      <section className="grid gap-4 sm:grid-cols-3">
        <StatCard title="Batches" value={formatNumber(plan.total_batches)} />
        <StatCard
          title="Total hourglasses"
          value={formatNumber(plan.total_hourglasses)}
          hint={`${doc.hourglass_per_pack} per pack`}
        />
        <StatCard title="Start with" value={plan.top_pack_name} />
      </section>

      <div className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">#</TableHead>
              <TableHead>Pack</TableHead>
              <TableHead className="text-right">Packs</TableHead>
              <TableHead className="text-right">Cost</TableHead>
              <TableHead className="text-right">Unified</TableHead>
              <TableHead>Notes</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {plan.batches.map((b) => (
              <TableRow key={b.batch_number}>
                <TableCell className="tabular-nums text-muted-foreground">
                  {b.batch_number}
                </TableCell>
                <TableCell>
                  <div className="font-medium">{b.pack_name}</div>
                  <div className="text-xs text-muted-foreground">
                    {b.expansion}
                  </div>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {b.packs_to_open}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatNumber(b.hourglass_cost)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatEv(b.unified_score)}
                </TableCell>
                <TableCell className="max-w-md text-xs text-muted-foreground">
                  {b.notes}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <p className="text-sm text-muted-foreground">
        <span className="font-medium text-foreground">Stop when: </span>
        {plan.stopping_condition}
      </p>
    </div>
  );
}
