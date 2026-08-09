import { Suspense } from "react";
import Link from "next/link";

import { Nav } from "@/components/layout/nav";
import { NavList } from "@/components/layout/nav-list";
import { SidebarInitScript } from "@/components/layout/sidebar-state";
import { SidebarToggle } from "@/components/layout/sidebar-toggle";
import { TopBar } from "@/components/layout/top-bar";
import { Pokeball } from "@/components/brand/pokeball";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <SidebarInitScript />
      {/* Width and label visibility come from CSS keyed on <html data-sidebar>,
          so this whole shell stays statically prerenderable. */}
      {/* Sticky and self-start: as a stretched flex child the rail grew to the
          full page height, which pushed the toggle below the fold on long pages. */}
      <aside className="sidebar-rail sticky top-0 hidden h-dvh shrink-0 self-start overflow-y-auto border-r bg-sidebar text-sidebar-foreground md:flex md:flex-col">
        <Link
          href="/"
          className="sidebar-row flex items-center gap-2 border-b px-5 py-4"
        >
          <Pokeball className="size-6 shrink-0" />
          <span className="sidebar-label font-heading text-[0.95rem] font-semibold tracking-tight leading-tight">
            TCGP Optimizer
          </span>
        </Link>
        <Suspense fallback={<NavList pathname={null} />}>
          <Nav />
        </Suspense>
        <div className="sidebar-row mt-auto flex justify-end border-t px-3 py-2">
          <SidebarToggle />
        </div>
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
