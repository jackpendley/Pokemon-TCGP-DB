"use client";

import { useState } from "react";

import { setLogoUrl } from "@/lib/domain/pack-image";
import { cn } from "@/lib/utils";

/**
 * Expansion logo (shared by the Packs table and the Sets pages). Degrades to a
 * set-code chip if the logo fails to load.
 */
export function SetLogo({
  setCode,
  label,
  className,
}: {
  setCode: string;
  label: string;
  className?: string;
}) {
  const [errored, setErrored] = useState(false);

  if (errored) {
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
      src={setLogoUrl(setCode)}
      alt={`${label} logo`}
      loading="lazy"
      onError={() => setErrored(true)}
      className={cn("object-contain", className)}
    />
  );
}
