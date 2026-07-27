"use server";

import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { createSupabaseServerClient } from "@/lib/auth/server";

export type LoginState = { error: string } | null;

/** Owner sign-in. On success sets the session cookie and redirects home. */
export async function login(
  _prev: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const email = String(formData.get("email") ?? "");
  const password = String(formData.get("password") ?? "");

  const supabase = await createSupabaseServerClient();
  const { error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) return { error: error.message };

  // redirect() throws to unwind — must live outside any try/catch.
  redirect("/");
}

export async function logout() {
  const supabase = await createSupabaseServerClient();
  await supabase.auth.signOut();
  redirect("/");
}

export type ResetState = { error: string } | { sent: true } | null;

/**
 * Send a password-recovery email.
 *
 * Always reports success, even for an address with no account: telling a
 * stranger whether an email is registered is an account-enumeration leak, and
 * this is a single-owner app where that answer is especially cheap to guess.
 *
 * The link lands on /auth/callback, which exchanges the PKCE code for a session
 * server-side and forwards to /reset-password. Doing the exchange there rather
 * than in the browser is what keeps the anon key server-only, matching how
 * sign-in already works here.
 */
export async function requestPasswordReset(
  _prev: ResetState,
  formData: FormData,
): Promise<ResetState> {
  const email = String(formData.get("email") ?? "").trim();
  if (!email) return { error: "Enter your email address." };

  const origin = (await headers()).get("origin");
  if (!origin) return { error: "Could not determine the site address." };

  const supabase = await createSupabaseServerClient();
  await supabase.auth.resetPasswordForEmail(email, {
    redirectTo: `${origin}/auth/callback?next=/reset-password`,
  });
  return { sent: true };
}

export type UpdatePasswordState = { error: string } | null;

/**
 * Set a new password for the session established by the recovery link.
 * Supabase rejects this without a valid session, so the recovery link itself is
 * the authorisation.
 */
export async function updatePassword(
  _prev: UpdatePasswordState,
  formData: FormData,
): Promise<UpdatePasswordState> {
  const password = String(formData.get("password") ?? "");
  const confirm = String(formData.get("confirm") ?? "");
  if (password.length < 8) return { error: "Use at least 8 characters." };
  if (password !== confirm) return { error: "Those passwords don't match." };

  const supabase = await createSupabaseServerClient();
  const { error } = await supabase.auth.updateUser({ password });
  if (error) return { error: error.message };

  redirect("/");
}
