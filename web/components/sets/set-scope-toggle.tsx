"use client";

import { Button } from "@/components/ui/button";

export type SetScope = "total" | "base";

/**
 * Full-set / Base-set switch shared by the Sets index and a single set page.
 * Base = base-rarity cards only (no secret/chase rarities).
 */
export function SetScopeToggle({
  scope,
  onChange,
}: {
  scope: SetScope;
  onChange: (scope: SetScope) => void;
}) {
  return (
    <div className="inline-flex rounded-md border p-0.5">
      {(["total", "base"] as SetScope[]).map((s) => (
        <Button
          key={s}
          type="button"
          size="sm"
          variant={scope === s ? "secondary" : "ghost"}
          className="h-7"
          onClick={() => onChange(s)}
        >
          {s === "total" ? "Full set" : "Base set"}
        </Button>
      ))}
    </div>
  );
}
