import { Suspense } from "react";
import Link from "next/link";

import { Nav } from "@/components/layout/nav";
import { NavList } from "@/components/layout/nav-list";
import { TopBar } from "@/components/layout/top-bar";
import { Pokeball } from "@/components/brand/pokeball";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 shrink-0 border-r bg-sidebar text-sidebar-foreground md:flex md:flex-col">
        <Link href="/" className="flex items-center gap-2 border-b px-5 py-4">
          <Pokeball className="size-6" />
          <span className="font-heading text-[0.95rem] font-semibold tracking-tight leading-tight">
            TCGP Optimizer
          </span>
        </Link>
        <Suspense fallback={<NavList pathname={null} />}>
          <Nav />
        </Suspense>
      </aside>
      <div className="flex flex-1 flex-col overflow-x-hidden">
        <TopBar />
        <main className="flex-1">
          {/* Tighter gutters on phones — 24px each side costs real width at 375px. */}
          <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
