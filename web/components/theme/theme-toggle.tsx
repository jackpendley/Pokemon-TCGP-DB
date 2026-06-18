"use client";

import { useTheme } from "next-themes";
import { Moon, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";

  return (
    <Button
      variant="ghost"
      size="sm"
      className="w-full justify-start gap-3 text-muted-foreground"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label="Toggle theme"
    >
      {/* Icons swap via CSS (.dark), so they're hydration-safe. */}
      <Sun className="size-4 shrink-0 dark:hidden" />
      <Moon className="hidden size-4 shrink-0 dark:block" />
      {/* Label depends on resolved theme (unknown during SSR); suppress the
          one-frame hydration diff rather than gating render behind an effect. */}
      <span suppressHydrationWarning>{isDark ? "Light mode" : "Dark mode"}</span>
    </Button>
  );
}
