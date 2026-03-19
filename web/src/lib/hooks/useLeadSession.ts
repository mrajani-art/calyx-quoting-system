"use client";

import { useState, useEffect } from "react";
import type { LeadData } from "@/lib/types/quote";

const STORAGE_KEY = "calyx_lead_session";

export function useLeadSession() {
  const [lead, setLead] = useState<LeadData | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        // Guard against stale sessions from pre-BIGINT migration where lead_id was a UUID string
        if (typeof parsed.lead_id !== "number") {
          localStorage.removeItem(STORAGE_KEY);
        } else {
          setLead(parsed);
        }
      } catch {
        localStorage.removeItem(STORAGE_KEY);
      }
    }
    setIsLoaded(true);
  }, []);

  const saveLead = (data: LeadData) => {
    setLead(data);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  };

  const clearLead = () => {
    setLead(null);
    localStorage.removeItem(STORAGE_KEY);
  };

  return { lead, saveLead, clearLead, isLoaded };
}
