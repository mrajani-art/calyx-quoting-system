import type {
  InstantQuoteResponse,
  LeadData,
  BagConfig,
} from "@/lib/types/quote";
import { QuoteError } from "./errors";

const API_BASE = "/api/v1";

export async function submitLead(
  data: Omit<LeadData, "lead_id">
): Promise<LeadData> {
  const res = await fetch(`${API_BASE}/leads`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new QuoteError(res.status, `Request failed with status ${res.status}`);
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
  if (!res.ok) throw new QuoteError(res.status, `Request failed with status ${res.status}`);
  return res.json();
}

export async function requestAccountManager(
  quoteId: string,
  leadId: string,
  note?: string,
  artworkUrl?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/quotes/request-manager`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ quote_id: quoteId, lead_id: leadId, note, artwork_url: artworkUrl }),
  });
  if (!res.ok) throw new QuoteError(res.status, `Request failed with status ${res.status}`);
}
