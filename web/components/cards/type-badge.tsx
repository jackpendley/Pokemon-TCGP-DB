import { typeColor } from "@/lib/domain/type-colors";

/** Small colored chip for a card's type (energy type or trainer subtype). */
export function TypeBadge({ type }: { type: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-[10px] text-muted-foreground">
      <span
        className="size-2 shrink-0 rounded-full"
        style={{ backgroundColor: typeColor(type) }}
      />
      <span className="truncate">{type}</span>
    </span>
  );
}
