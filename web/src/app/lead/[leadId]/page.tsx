import { notFound } from "next/navigation";
import { headers } from "next/headers";
import type { LeadDetailResponse } from "@/lib/types/lead-detail";
import LeadDetailView from "./LeadDetailView";

async function getLeadDetail(leadId: string): Promise<LeadDetailResponse | null> {
  try {
    const headersList = await headers();
    const proto = headersList.get("x-forwarded-proto") || "https";
    const host = headersList.get("host") || "localhost:3000";
    const origin = `${proto}://${host}`;

    const res = await fetch(`${origin}/api/v1/leads/${leadId}/detail`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function LeadDetailPage({
  params,
}: {
  params: Promise<{ leadId: string }>;
}) {
  const { leadId } = await params;
  const data = await getLeadDetail(leadId);

  if (!data) notFound();

  return <LeadDetailView data={data} />;
}
