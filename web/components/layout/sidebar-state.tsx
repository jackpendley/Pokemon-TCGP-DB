"use client";

import { useSyncExternalStore } from "react";

export const SIDEBAR_STORAGE_KEY = "sidebar-collapsed";

/**
 * Applies the saved sidebar width before first paint.
 *
 * The state can't come from a cookie read in the root layout: that would make
 * the whole layout dynamic and throw away the prerendered static shell the
 * routes now depend on. So it's stored client-side and stamped onto <html> by
 * this blocking script — the same approach next-themes already uses here to
 * avoid a theme flash. Rendering it inside <body> is fine; it runs before the
 * sidebar below it paints.
 */
export function SidebarInitScript() {
  return (
    <script
      dangerouslySetInnerHTML={{
        __html: `try{if(localStorage.getItem(${JSON.stringify(
          SIDEBAR_STORAGE_KEY,
        )})==="1")document.documentElement.dataset.sidebar="collapsed"}catch(e){}`,
      }}
    />
  );
}

function subscribe(onChange: () => void): () => void {
  const observer = new MutationObserver(onChange);
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-sidebar"],
  });
  return () => observer.disconnect();
}

const getSnapshot = () =>
  document.documentElement.dataset.sidebar === "collapsed";

/**
 * Whether the sidebar is collapsed. The attribute on <html> is the source of
 * truth — width is driven purely by CSS from it, so React state never gates the
 * layout — and this observes it for the bits that do need to re-render (the
 * toggle's own label and icon).
 */
export function useSidebarCollapsed(): boolean {
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}

export function setSidebarCollapsed(collapsed: boolean): void {
  document.documentElement.dataset.sidebar = collapsed ? "collapsed" : "expanded";
  try {
    localStorage.setItem(SIDEBAR_STORAGE_KEY, collapsed ? "1" : "0");
  } catch {
    // Private mode / storage disabled — the toggle still works for this session.
  }
}
