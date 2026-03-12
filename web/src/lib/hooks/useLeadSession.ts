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
        setLead(JSON.parse(stored));
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
