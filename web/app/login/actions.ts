"use server";

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
