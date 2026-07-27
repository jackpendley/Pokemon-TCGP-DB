import {
  LayoutDashboard,
  Layers,
  Package,
  Search,
  Swords,
  TrendingUp,
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
  { href: "/decks", label: "Decks", icon: Swords },
  { href: "/history", label: "History", icon: TrendingUp },
];
