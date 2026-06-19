import { cn } from "@/lib/utils";

/** Simple Poké Ball mark. Top half uses the primary (red) token. */
export function Pokeball({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={cn("size-5", className)}
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="11" className="fill-card stroke-foreground" strokeWidth="1.5" />
      <path
        d="M1 12a11 11 0 0 1 22 0Z"
        className="fill-primary stroke-foreground"
        strokeWidth="1.5"
      />
      <line x1="1" y1="12" x2="8" y2="12" className="stroke-foreground" strokeWidth="1.5" />
      <line x1="16" y1="12" x2="23" y2="12" className="stroke-foreground" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="3.4" className="fill-card stroke-foreground" strokeWidth="1.5" />
      <circle cx="12" cy="12" r="1.4" className="fill-foreground" />
    </svg>
  );
}
