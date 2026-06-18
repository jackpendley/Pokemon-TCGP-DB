import Link from "next/link";
import { Sparkles } from "lucide-react";

import { Nav } from "@/components/layout/nav";
import { ThemeToggle } from "@/components/theme/theme-toggle";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 shrink-0 border-r bg-sidebar text-sidebar-foreground md:flex md:flex-col">
        <Link href="/" className="flex items-center gap-2 border-b px-5 py-4">
          <Sparkles className="size-5 text-primary" />
          <span className="font-semibold leading-tight">
            TCGP Optimizer
          </span>
        </Link>
        <Nav />
        <div className="mt-auto border-t p-2">
          <ThemeToggle />
        </div>
      </aside>
      <main className="flex-1 overflow-x-hidden">
        <div className="mx-auto w-full max-w-6xl px-6 py-8">{children}</div>
      </main>
    </div>
  );
}
