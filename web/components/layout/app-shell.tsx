import Link from "next/link";

import { Nav } from "@/components/layout/nav";
import { TopBar } from "@/components/layout/top-bar";
import { Pokeball } from "@/components/brand/pokeball";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-64 shrink-0 border-r bg-sidebar text-sidebar-foreground md:flex md:flex-col">
        <Link href="/" className="flex items-center gap-2 border-b px-5 py-4">
          <Pokeball className="size-6" />
          <span className="font-semibold leading-tight">TCGP Optimizer</span>
        </Link>
        <Nav />
      </aside>
      <div className="flex flex-1 flex-col overflow-x-hidden">
        <TopBar />
        <main className="flex-1">
          <div className="mx-auto w-full max-w-6xl px-6 py-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
