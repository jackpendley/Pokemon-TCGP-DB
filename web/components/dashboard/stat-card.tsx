import Link from "next/link";
import { Info } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export function StatCard({
  title,
  value,
  hint,
  info,
  href,
  align = "left",
}: {
  title: string;
  value: string;
  hint?: string;
  info?: string;
  /** When set, the whole card links here (with hover affordance). */
  href?: string;
  align?: "left" | "center";
}) {
  const centered = align === "center";
  const card = (
    <Card className={cn("h-full", href && "transition-colors hover:border-primary/50")}>
      <CardHeader className="pb-2">
        <CardTitle
          className={cn(
            "flex items-center gap-1.5 text-sm font-medium text-muted-foreground",
            centered && "justify-center",
          )}
        >
          {title}
          {info ? (
            <Tooltip>
              <TooltipTrigger
                className="text-muted-foreground/70 hover:text-foreground"
                aria-label={`About ${title}`}
              >
                <Info className="size-3.5" />
              </TooltipTrigger>
              <TooltipContent>{info}</TooltipContent>
            </Tooltip>
          ) : null}
        </CardTitle>
      </CardHeader>
      <CardContent className={cn(centered && "text-center")}>
        <div className="text-2xl font-semibold tabular-nums">{value}</div>
        {hint ? (
          <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
        ) : null}
      </CardContent>
    </Card>
  );
  return href ? (
    <Link href={href} className="block">
      {card}
    </Link>
  ) : (
    card
  );
}
