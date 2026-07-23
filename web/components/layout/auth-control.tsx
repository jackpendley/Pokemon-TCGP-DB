import Link from "next/link";

import { logout } from "@/app/login/actions";
import { Button } from "@/components/ui/button";
import { isOwner } from "@/lib/auth/server";

/**
 * Owner sees a Sign out button; everyone else a Sign in link. Rendered in the
 * TopBar. Async Server Component — reads the session per request.
 */
export async function AuthControl() {
  const owner = await isOwner();

  if (owner) {
    return (
      <form action={logout}>
        <Button type="submit" variant="ghost" size="sm">
          Sign out
        </Button>
      </form>
    );
  }

  return (
    <Button render={<Link href="/login" />} variant="ghost" size="sm">
      Sign in
    </Button>
  );
}
