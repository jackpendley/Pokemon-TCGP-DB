"use client";

import { PanelLeftClose, PanelLeftOpen } from "lucide-react";

import {
  setSidebarCollapsed,
  useSidebarCollapsed,
} from "@/components/layout/sidebar-state";
import { Button } from "@/components/ui/button";

/** Collapses the sidebar to an icon rail, or restores it. */
export function SidebarToggle() {
  const collapsed = useSidebarCollapsed();
  const label = collapsed ? "Expand sidebar" : "Collapse sidebar";

  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={label}
      aria-pressed={collapsed}
      title={label}
      onClick={() => setSidebarCollapsed(!collapsed)}
    >
      {collapsed ? (
        <PanelLeftOpen className="size-4" />
      ) : (
        <PanelLeftClose className="size-4" />
      )}
    </Button>
  );
}
