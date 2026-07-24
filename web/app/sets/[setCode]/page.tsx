import { Suspense } from "react";
import { redirect } from "next/navigation";

// The per-set card view is now the unified Cards page filtered by set, so a
// set's cards live on the same page as `/cards?set=…`. Old links redirect.
async function SetRedirect({
  params,
}: {
  params: Promise<{ setCode: string }>;
}) {
  const { setCode } = await params;
  return redirect(
    `/cards?set=${encodeURIComponent(decodeURIComponent(setCode))}`,
  );
}

export default function SetDetailPage({
  params,
}: {
  params: Promise<{ setCode: string }>;
}) {
  // params is per-request; defer it to runtime so the build prerenders cleanly.
  return (
    <Suspense>
      <SetRedirect params={params} />
    </Suspense>
  );
}
