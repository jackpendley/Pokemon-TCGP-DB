import { SetsGrid, type SetProgress } from "@/components/sets/sets-grid";
import { dataSource } from "@/lib/data";
import { isBaseRarity } from "@/lib/domain/rarity";

export const dynamic = "force-dynamic";
export const metadata = { title: "Sets · TCGP Optimizer" };

export default async function SetsPage() {
  const catalog = await dataSource.getCatalog();

  // Preserve first-seen order (≈ release order) while aggregating per set.
  const bySet = new Map<string, SetProgress>();
  for (const c of catalog) {
    let s = bySet.get(c.set_code);
    if (!s) {
      s = {
        set_code: c.set_code,
        expansion: c.expansion,
        total: 0,
        owned: 0,
        baseTotal: 0,
        baseOwned: 0,
      };
      bySet.set(c.set_code, s);
    }
    s.total += 1;
    if (c.owned > 0) s.owned += 1;
    if (isBaseRarity(c.rarity)) {
      s.baseTotal += 1;
      if (c.owned > 0) s.baseOwned += 1;
    }
  }
  const sets = [...bySet.values()];

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Set Completion</h1>
        <p className="text-sm text-muted-foreground">
          Unique cards owned per set ({sets.length} sets). Toggle between the full
          set and the base set (no secret/chase rarities).
        </p>
      </header>

      <SetsGrid sets={sets} />
    </div>
  );
}
