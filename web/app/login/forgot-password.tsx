"use client";

import { useActionState, useState } from "react";

import { Button } from "@/components/ui/button";
import { requestPasswordReset, type ResetState } from "./actions";

/**
 * Collapsed by default so it doesn't compete with the sign-in form — this is
 * the rare path, and the common one shouldn't have to scroll past it.
 */
export function ForgotPassword() {
  const [open, setOpen] = useState(false);
  const [state, formAction, pending] = useActionState<ResetState, FormData>(
    requestPasswordReset,
    null,
  );

  if (state && "sent" in state) {
    return (
      <p className="mt-4 text-sm text-muted-foreground">
        If that address has an account, a recovery link is on its way. The link
        expires after a short while.
      </p>
    );
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-4 text-sm text-muted-foreground hover:text-foreground hover:underline"
      >
        Forgot password?
      </button>
    );
  }

  return (
    <form action={formAction} className="mt-4 space-y-2 border-t pt-4">
      <label htmlFor="reset-email" className="text-sm font-medium">
        Send a recovery link
      </label>
      <input
        id="reset-email"
        name="email"
        type="email"
        autoComplete="email"
        required
        placeholder="you@example.com"
        className="h-9 w-full rounded-md border bg-background px-3 text-sm"
      />
      {state?.error ? (
        <p className="text-sm text-destructive">{state.error}</p>
      ) : null}
      <Button
        type="submit"
        variant="outline"
        disabled={pending}
        className="w-full"
      >
        {pending ? "Sending…" : "Email me a link"}
      </Button>
    </form>
  );
}
