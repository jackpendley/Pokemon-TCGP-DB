import { cn } from "@/lib/utils";
import { raritySymbol } from "@/lib/domain/rarity";

/**
 * Hand-built SVG replicas of the in-app TCG Pocket rarity symbols. The real game
 * art isn't on a hot-linkable CDN, so these match the shapes (brilliant-cut
 * diamond, 5-point star, crown, 4-point shiny sparkle) and tier colours closely.
 */

type IconProps = { className?: string };

// Simple solid diamond (the in-app symbol is a flat rhombus, not a faceted gem),
// with a subtle top highlight for a hint of depth.
function GemIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path d="M12 2 19.5 12 12 22 4.5 12Z" fill="currentColor" />
      <path d="M12 2 19.5 12 12 12Z" fill="#fff" fillOpacity="0.28" />
    </svg>
  );
}

function StarIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path
        d="M12 2l2.95 6.36 6.95.68-5.2 4.66 1.5 6.84L12 17.6l-6.2 3.54 1.5-6.84-5.2-4.66 6.95-.68z"
        fill="currentColor"
      />
    </svg>
  );
}

function CrownIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path
        d="M2 8l4.5 3L12 4l5.5 7L22 8l-2 11H4z"
        fill="currentColor"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// 4-point sparkle for shiny rarities.
function SparkleIcon({ className }: IconProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path
        d="M12 1.5c.55 5 3.5 7.95 8.5 8.5-5 .55-7.95 3.5-8.5 8.5-.55-5-3.5-7.95-8.5-8.5 5-.55 7.95-3.5 8.5-8.5z"
        fill="currentColor"
      />
    </svg>
  );
}

const ICONS = {
  diamond: GemIcon,
  star: StarIcon,
  crown: CrownIcon,
  sparkle: SparkleIcon,
  // Promo cards carry a dark star stamp in-app — a slate star is the closest match.
  promo: StarIcon,
} as const;

const COLORS = {
  diamond: "text-teal-500",
  star: "text-amber-400",
  crown: "text-amber-500",
  sparkle: "text-fuchsia-400",
  promo: "text-slate-500",
} as const;

/**
 * Renders a rarity's symbol: 1–4 diamonds, 1–3 stars, crown, shiny sparkles,
 * or a slate promo star.
 */
export function RaritySymbol({
  rarity,
  className,
}: {
  rarity: string | null;
  className?: string;
}) {
  const { kind, count } = raritySymbol(rarity);
  const Icon = ICONS[kind];

  return (
    <span className={cn("inline-flex items-center gap-px", COLORS[kind], className)}>
      {Array.from({ length: count }).map((_, i) => (
        <Icon key={i} className="size-3.5" />
      ))}
    </span>
  );
}
