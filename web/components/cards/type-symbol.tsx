import {
  Cog,
  Droplet,
  Eye,
  Flame,
  Gem,
  Leaf,
  Moon,
  Star,
  Swords,
  Zap,
  type LucideIcon,
} from "lucide-react";

import { typeColor } from "@/lib/domain/type-colors";
import { cn } from "@/lib/utils";

/**
 * A small energy-type badge: a type-coloured disc with a themed glyph, approximating
 * the in-game energy symbols (whose art isn't hot-linkable, like RaritySymbol).
 */
const TYPE_ICONS: Record<string, LucideIcon> = {
  Grass: Leaf,
  Fire: Flame,
  Water: Droplet,
  Lightning: Zap,
  Psychic: Eye,
  Fighting: Swords,
  Darkness: Moon,
  Metal: Cog,
  Dragon: Gem,
  Colorless: Star,
};

/** Canonical in-game energy order, for stable ordering of the type filter. */
export const ENERGY_TYPES = Object.keys(TYPE_ICONS);

export function TypeSymbol({
  type,
  className,
}: {
  type: string;
  className?: string;
}) {
  const Icon = TYPE_ICONS[type] ?? Star;
  return (
    <span
      className={cn(
        "inline-flex size-5 shrink-0 items-center justify-center rounded-full",
        className,
      )}
      style={{ backgroundColor: typeColor(type) }}
      aria-hidden="true"
    >
      <Icon className="size-3 text-white" strokeWidth={2.5} />
    </span>
  );
}
