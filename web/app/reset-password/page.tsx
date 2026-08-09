import { Suspense } from "react";
import Link from "next/link";
import { connection } from "next/server";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TextLinesSkeleton } from "@/components/ui/skeletons";
import { getSessionUser } from "@/lib/auth/server";
import { ResetPasswordForm } from "./reset-password-form";

export const metadata = { title: "Set a new password · TCGP Optimizer" };

/**
 * Reads the session cookie /auth/callback just set, so it has to sit inside a
 * Suspense boundary — under Cache Components, uncached data at the top level of
 * a page blocks the whole route from prerendering.
 */
async function ResetContent() {
  await connection();
  const user = await getSessionUser();

  if (!user) {
    return (
      <div className="space-y-3 text-sm text-muted-foreground">
        <p>
          This recovery link has expired or was already used. Request a new one
          from the sign-in page.
        </p>
        <Link href="/login" className="text-primary hover:underline">
          Back to sign in
        </Link>
      </div>
    );
  }
  return <ResetPasswordForm email={user.email ?? ""} />;
}

export default function ResetPasswordPage() {
  return (
    <div className="mx-auto max-w-sm py-10">
      <Card>
        <CardHeader>
          <CardTitle>Set a new password</CardTitle>
        </CardHeader>
        <CardContent>
          <Suspense fallback={<TextLinesSkeleton lines={3} width="w-full" />}>
            <ResetContent />
          </Suspense>
        </CardContent>
      </Card>
    </div>
  );
}
