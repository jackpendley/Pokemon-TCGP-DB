import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/**
 * Layout-matched Suspense fallbacks.
 *
 * These deliberately mirror the real component's box model — same grid columns,
 * same aspect ratios, same card chrome — so when the streamed content lands it
 * replaces the placeholder in place instead of reflowing the page. A generic
 * `<Skeleton className="h-96 w-full" />` reads as a loading slab; these read as
 * the page already being there.
 *
 * Rule of thumb when adding one: render the real wrapper elements (Card,
 * CardHeader, the grid div) and only substitute Skeleton for the text and
 * imagery inside.
 */

/** Grid of card-art tiles at the same breakpoints as CardGrid / RevealGrid. */
export function CardTileGridSkeleton({
  count = 12,
  className,
}: {
  count?: number;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5",
        className,
      )}
    >
      {Array.from({ length: count }, (_, i) => (
        <Skeleton key={i} className="aspect-[5/7] w-full rounded-lg" />
      ))}
    </div>
  );
}

/** Header row plus body rows, sized to a real bordered table. */
export function TableSkeleton({
  rows = 8,
  columns = 5,
  className,
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) {
  return (
    <div className={cn("overflow-hidden rounded-xl border", className)}>
      <div className="flex gap-4 border-b bg-muted/40 px-4 py-3">
        {Array.from({ length: columns }, (_, i) => (
          <Skeleton
            key={i}
            className={cn("h-4", i === 0 ? "w-40 flex-none" : "w-full flex-1")}
          />
        ))}
      </div>
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} className="flex items-center gap-4 border-b px-4 py-3.5 last:border-b-0">
          {Array.from({ length: columns }, (_, i) => (
            <Skeleton
              key={i}
              className={cn("h-4", i === 0 ? "w-40 flex-none" : "w-full flex-1")}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

/** Row of StatCard-shaped tiles (title line + value line inside real Card chrome). */
export function StatTilesSkeleton({
  count = 4,
  className,
}: {
  count?: number;
  className?: string;
}) {
  return (
    <div className={cn("grid grid-cols-2 gap-4 sm:grid-cols-4", className)}>
      {Array.from({ length: count }, (_, i) => (
        <Card key={i} className="h-full">
          <CardHeader className="pb-2">
            <Skeleton className="mx-auto h-4 w-20" />
          </CardHeader>
          <CardContent className="text-center">
            <Skeleton className="mx-auto h-7 w-16" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

/**
 * A Card-shaped placeholder with a title line. `bodyClassName` sets the body
 * height so it matches whatever it stands in for.
 */
export function PanelSkeleton({
  titleWidth = "w-32",
  bodyClassName = "h-40",
  className,
}: {
  titleWidth?: string;
  bodyClassName?: string;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <Skeleton className={cn("h-5", titleWidth)} />
      </CardHeader>
      <CardContent>
        <Skeleton className={cn("w-full rounded-lg", bodyClassName)} />
      </CardContent>
    </Card>
  );
}

/** Grid of small labelled count cells, matching CountGrid's inner layout. */
export function CountGridSkeleton({
  cells = 9,
  titleWidth = "w-40",
  className,
}: {
  cells?: number;
  titleWidth?: string;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <Skeleton className={cn("h-5", titleWidth)} />
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {Array.from({ length: cells }, (_, i) => (
            <div
              key={i}
              className="flex flex-col gap-1.5 rounded-lg bg-muted/40 px-3 py-2.5"
            >
              <Skeleton className="h-3 w-16" />
              <Skeleton className="h-5 w-12" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/** One or more plain text lines, for inline metadata that streams in. */
export function TextLinesSkeleton({
  lines = 1,
  width = "w-56",
  className,
}: {
  lines?: number;
  width?: string;
  className?: string;
}) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} className={cn("h-4", width)} />
      ))}
    </div>
  );
}
