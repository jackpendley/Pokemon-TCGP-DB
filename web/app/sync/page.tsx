import { redirect } from "next/navigation";

// Sync Status is now merged into the Dashboard; old links redirect there.
export default function SyncPage() {
  redirect("/");
}
