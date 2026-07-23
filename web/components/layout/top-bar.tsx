import Link from "next/link";

import { AuthControl } from "@/components/layout/auth-control";
import { MobileNav } from "@/components/layout/mobile-nav";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { Pokeball } from "@/components/brand/pokeball";

/** Sticky header present on every viewport so the theme toggle (and, on mobile,
 *  navigation) is always reachable. */
export function TopBar() {
  return (
    <header className="sticky top-0 z-40 flex h-14 items-center gap-2 border-b bg-background/80 px-4 backdrop-blur">
      <MobileNav />
      <Link href="/" className="flex items-center gap-2 md:hidden">
        <Pokeball />
        <span className="font-semibold">TCGP Optimizer</span>
      </Link>
      <div className="ml-auto flex items-center gap-1">
        <AuthControl />
        <ThemeToggle />
      </div>
    </header>
  );
}
