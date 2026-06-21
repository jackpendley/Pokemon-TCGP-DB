import { Crown, Diamond, Sparkles, Star } from "lucide-react";

import { cn } from "@/lib/utils";
import { raritySymbol } from "@/lib/domain/rarity";

const ICONS = {
  diamond: Diamond,
  star: Star,
  crown: Crown,
  sparkle: Sparkles,
  promo: Star,
} as const;

const COLORS = {
  diamond: "text-sky-500",
  star: "text-amber-500",
  crown: "text-yellow-500",
  sparkle: "text-cyan-400",
  promo: "text-muted-foreground",
} as const;

/**
 * Renders a rarity's in-app symbol (1–4 diamonds, 1–3 stars, crown, shiny
 * sparkles) as composed lucide icons. Promo has no tier symbol → a "P" chip.
 */
export function RaritySymbol({
  rarity,
  className,
}: {
  rarity: string | null;
  className?: string;
}) {
  const { kind, count } = raritySymbol(rarity);

  if (kind === "promo") {
    return (
      <span
        className={cn(
          "inline-flex size-3.5 items-center justify-center rounded-[3px] bg-muted text-[9px] font-bold text-muted-foreground",
          className,
        )}
      >
        P
      </span>
    );
  }

  const Icon = ICONS[kind];
  return (
    <span className={cn("inline-flex items-center gap-px", className)}>
      {Array.from({ length: count }).map((_, i) => (
        <Icon key={i} className={cn("size-3.5 fill-current", COLORS[kind])} />
      ))}
    </span>
  );
}
