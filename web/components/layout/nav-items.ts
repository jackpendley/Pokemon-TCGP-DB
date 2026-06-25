import {
  LayoutDashboard,
  Package,
  Layers,
  Wallet,
  Search,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/packs", label: "Pack Recommendations", icon: Package },
  { href: "/cards", label: "Cards", icon: Search },
  { href: "/sets", label: "Sets", icon: Layers },
  { href: "/plan", label: "Spending Plan", icon: Wallet },
];
