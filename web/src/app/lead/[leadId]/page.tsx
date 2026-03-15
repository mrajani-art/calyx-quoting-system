import { notFound } from "next/navigation";
import type { LeadDetailResponse } from "@/lib/types/lead-detail";
import LeadDetailView from "./LeadDetailView";

const API_URL = process.env.API_URL || "http://localhost:8000";

async function getLeadDetail(leadId: string): Promise<LeadDetailResponse | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/leads/${leadId}/detail`, {
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
