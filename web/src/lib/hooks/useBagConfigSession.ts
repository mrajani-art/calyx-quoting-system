"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { DEFAULTS } from "@/lib/constants/bag-options";
import { DEFAULT_ACTIVE_QTY } from "@/lib/constants/method-config";

const STORAGE_KEY = "calyx_bag_config";
const DEFAULT_TIERS = [5_000, 10_000, 25_000, 50_000, 100_000, 250_000];

export interface BagConfigSession {
  selectedSize: { w: number; h: number; g: number } | null;
  isCustomSize: boolean;
  customWidth: number;
  customHeight: number;
  customGusset: number;
  substrate: string;
  finish: string;
  sealType: string;
  fillStyle: string;
  gussetType: string;
  zipper: string;
  tearNotch: string;
  holePunch: string;
  corners: string;
  embellishment: string;
  selectedTiers: number[];
  activeTier: number;
}

const DEFAULT_CONFIG: BagConfigSession = {
  selectedSize: { w: 4.5, h: 5, g: 2 },
  isCustomSize: false,
  customWidth: 4.5,
  customHeight: 5,
  customGusset: 2,
  substrate: DEFAULTS.substrate,
  finish: DEFAULTS.finish,
  sealType: DEFAULTS.sealType,
  fillStyle: DEFAULTS.fillStyle,
  gussetType: DEFAULTS.gussetType,
  zipper: DEFAULTS.zipper,
  tearNotch: DEFAULTS.tearNotch,
  holePunch: DEFAULTS.holePunch,
  corners: DEFAULTS.corners,
  embellishment: DEFAULTS.embellishment,
  selectedTiers: DEFAULT_TIERS,
  activeTier: DEFAULT_ACTIVE_QTY,
};

export function useBagConfigSession() {
  const [config, setConfig] = useState<BagConfigSession>(DEFAULT_CONFIG);
  const [isLoaded, setIsLoaded] = useState(false);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as Partial<BagConfigSession>;
        setConfig((prev) => ({ ...prev, ...parsed }));
      }
    } catch {
      // Ignore parse errors
    }
    setIsLoaded(true);
  }, []);

  // Debounced save to localStorage
  const saveConfig = useCallback((updates: Partial<BagConfigSession>) => {
    setConfig((prev) => {
      const next = { ...prev, ...updates };
      // Debounce localStorage writes
      if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = setTimeout(() => {
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        } catch {
          // Ignore storage errors
        }
      }, 500);
      return next;
    });
  }, []);

  return { config, saveConfig, isLoaded };
}
