import { redirect } from "next/navigation";

// The per-set card view is now the unified Cards page filtered by set, so a
// set's cards live on the same page as `/cards?set=…`. Old links redirect.
export default async function SetDetailPage({
  params,
}: {
  params: Promise<{ setCode: string }>;
}) {
  const { setCode } = await params;
  redirect(`/cards?set=${encodeURIComponent(decodeURIComponent(setCode))}`);
}
