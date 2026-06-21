"use client";

import { useState } from "react";

import { packLogoUrl } from "@/lib/domain/pack-image";
import { cn } from "@/lib/utils";

/**
 * Expansion logo shown beside a pack name. Degrades to a set-code chip when the
 * logo is missing (uncovered set) or fails to load.
 */
export function PackLogo({
  setCode,
  name,
  className,
}: {
  setCode: string;
  name: string;
  className?: string;
}) {
  const url = packLogoUrl(setCode);
  const [errored, setErrored] = useState(false);

  if (!url || errored) {
    return (
      <span
        className={cn(
          "flex items-center justify-center rounded bg-muted text-[10px] font-semibold text-muted-foreground",
          className,
        )}
      >
        {setCode}
      </span>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element -- external CDN hot-link with onError fallback.
    <img
      src={url}
      alt={`${name} pack`}
      loading="lazy"
      onError={() => setErrored(true)}
      className={cn("object-contain", className)}
    />
  );
}
