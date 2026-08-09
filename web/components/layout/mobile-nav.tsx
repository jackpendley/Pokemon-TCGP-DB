"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/components/layout/nav-items";

/** Static hamburger for the Suspense fallback while <MobileNav> streams in. */
export function MobileNavFallback() {
  return (
    <div className="md:hidden">
      <Button variant="ghost" size="icon" aria-label="Open navigation">
        <Menu className="size-5" />
      </Button>
    </div>
  );
}

/**
 * Hamburger menu for viewports where the sidebar is hidden (< md).
 *
 * Built on the Dialog primitive rather than a hand-rolled fixed overlay, which
 * is what gives it a focus trap, Escape-to-close, body scroll lock and an
 * enter/exit transition — none of which the previous overlay had.
 */
export function MobileNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <div className="md:hidden">
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogTrigger
          render={<Button variant="ghost" size="icon" />}
          aria-label="Open navigation"
        >
          <Menu className="size-5" />
        </DialogTrigger>

        {/* Anchored left as a drawer instead of the default centred popup. */}
        <DialogContent className="inset-y-0 top-0 left-0 h-dvh w-64 max-w-[80vw] translate-x-0 translate-y-0 rounded-none bg-sidebar p-3 text-sidebar-foreground">
          <DialogHeader className="px-2 py-1">
            <DialogTitle>Menu</DialogTitle>
          </DialogHeader>

          <nav className="flex flex-col gap-1">
            {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
              const active =
                href === "/" ? pathname === "/" : pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setOpen(false)}
                  className={cn(
                    // 44px min height keeps these comfortable touch targets.
                    "flex min-h-11 items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    active
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-muted-foreground hover:bg-sidebar-accent/50 hover:text-foreground",
                  )}
                >
                  <Icon className="size-4 shrink-0" />
                  {label}
                </Link>
              );
            })}
          </nav>
        </DialogContent>
      </Dialog>
    </div>
  );
}
