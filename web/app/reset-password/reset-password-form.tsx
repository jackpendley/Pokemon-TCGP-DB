"use client";

import { useActionState } from "react";

import { Button } from "@/components/ui/button";
import { updatePassword, type UpdatePasswordState } from "@/app/login/actions";

const inputCls = "h-9 w-full rounded-md border bg-background px-3 text-sm";

export function ResetPasswordForm({ email }: { email: string }) {
  const [state, formAction, pending] = useActionState<
    UpdatePasswordState,
    FormData
  >(updatePassword, null);

  return (
    <form action={formAction} className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Signed in from a recovery link as{" "}
        <span className="font-medium text-foreground">{email}</span>.
      </p>
      <div className="space-y-1">
        <label htmlFor="password" className="text-sm font-medium">
          New password
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          className={inputCls}
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="confirm" className="text-sm font-medium">
          Confirm password
        </label>
        <input
          id="confirm"
          name="confirm"
          type="password"
          autoComplete="new-password"
          required
          minLength={8}
          className={inputCls}
        />
      </div>
      {state?.error ? (
        <p className="text-sm text-destructive">{state.error}</p>
      ) : null}
      <Button type="submit" disabled={pending} className="w-full">
        {pending ? "Saving…" : "Set password"}
      </Button>
    </form>
  );
}
