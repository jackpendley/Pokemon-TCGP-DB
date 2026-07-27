import { cn } from "@/lib/utils";

/**
 * How many copies of a card you hold, as a compact "2x" chip.
 *
 * Deliberately renders nothing for zero: card art is already greyscaled when
 * unowned, so a "0x" would only restate it, and the chip is most useful when it
 * is rare enough to notice. Callers that need an explicit "not owned" should say
 * so themselves rather than passing 0 here.
 */
export function OwnedChip({
  owned,
  className,
}: {
  owned: number;
  className?: string;
}) {
  if (owned <= 0) return null;
  return (
    <span
      title={`You own ${owned}`}
      className={cn(
        "shrink-0 rounded bg-muted px-1 text-[10px] font-semibold text-foreground tabular-nums",
        className,
      )}
    >
      {owned}x
    </span>
  );
}
