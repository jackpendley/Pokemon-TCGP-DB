import Link from "next/link";

import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "@/components/layout/nav-items";
import { NavPending } from "@/components/layout/nav-pending";

/**
 * Presentational sidebar nav. Split out so it renders statically with
 * `pathname={null}` as the Suspense fallback (no active highlight) while the
 * pathname-aware <Nav> streams in — keeps the layout shell prerenderable under
 * Cache Components.
 *
 * Collapsed state isn't a prop: `sidebar-row` / `sidebar-label` are styled from
 * the `data-sidebar` attribute on <html>, so this stays a static component and
 * the rail can't flash the wrong width on load.
 */
export function NavList({ pathname }: { pathname: string | null }) {
  return (
    <nav className="flex flex-col gap-1 p-3">
      {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const active = pathname
          ? href === "/"
            ? pathname === "/"
            : pathname.startsWith(href)
          : false;
        return (
          <Link
            key={href}
            href={href}
            // Surfaces the label as a tooltip when the rail is collapsed.
            title={label}
            className={cn(
              "sidebar-row flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
            )}
          >
            <Icon className="size-4 shrink-0" />
            <span className="sidebar-label">{label}</span>
            <span className="sidebar-label contents">
              <NavPending />
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
