"use client";

import { usePathname } from "next/navigation";

import { NavList } from "@/components/layout/nav-list";

export function Nav() {
  return <NavList pathname={usePathname()} />;
}
