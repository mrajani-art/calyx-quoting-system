import type {
  InstantQuoteResponse,
  LeadData,
  BagConfig,
} from "@/lib/types/quote";

const API_BASE = "/api/v1";

export async function submitLead(
  data: Omit<LeadData, "lead_id">
): Promise<LeadData> {
  const res = await fetch(`${API_BASE}/leads`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to submit lead");
  const json = await res.json();
  return { ...data, lead_id: json.lead_id };
}

export async function getInstantQuote(
  config: BagConfig,
  leadId: string
): Promise<InstantQuoteResponse> {
  const res = await fetch(`${API_BASE}/quotes/instant`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...config, lead_id: leadId }),
  });
  if (!res.ok) throw new Error("Failed to get quote");
  return res.json();
}
