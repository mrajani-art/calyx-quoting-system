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
  if (!res.ok) {
    let detail = "Failed to submit lead";
    try { const body = await res.json(); if (body.detail) detail = body.detail; } catch {}
    throw new QuoteError(res.status, detail);
  }
  const json = await res.json();
  return { ...data, lead_id: json.lead_id };
}

export async function getInstantQuote(
  config: BagConfig,
  leadId: number
): Promise<InstantQuoteResponse> {
  const res = await fetch(`${API_BASE}/quotes/instant`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...config, lead_id: leadId }),
  });
  if (!res.ok) {
    let detail = "Failed to get quote";
    try { const body = await res.json(); if (body.detail) detail = body.detail; } catch {}
    throw new QuoteError(res.status, detail);
  }
  return res.json();
}

export async function uploadFiles(
  leadId: number,
  quoteId: number | null,
  files: File[]
): Promise<{ uploaded: { id: number; file_name: string; public_url: string }[] }> {
  const formData = new FormData();
  formData.append("lead_id", String(leadId));
  if (quoteId) formData.append("quote_id", String(quoteId));
  files.forEach((file) => formData.append("files", file));

  const res = await fetch(`${API_BASE}/files/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    let detail = "File upload failed";
    try { const body = await res.json(); if (body.detail) detail = body.detail; } catch {}
    throw new QuoteError(res.status, detail);
  }
  return res.json();
}

export async function requestAccountManager(
  quoteId: number,
  leadId: number,
  note?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/quotes/request-manager`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ quote_id: quoteId, lead_id: leadId, note }),
  });
  if (!res.ok) {
    let detail = "Failed to request account manager";
    try { const body = await res.json(); if (body.detail) detail = body.detail; } catch {}
    throw new QuoteError(res.status, detail);
  }
}
