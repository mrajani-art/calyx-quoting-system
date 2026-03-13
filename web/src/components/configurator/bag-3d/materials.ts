"use client";

import { useMemo } from "react";
import { MeshPhysicalMaterial, DoubleSide } from "three";
import { SUBSTRATE_MATERIALS, FINISH_MODIFIERS } from "./types";

/**
 * Returns a memoized MeshPhysicalMaterial configured for the given
 * substrate + finish combination.
 */
export function useBagMaterial(
  substrate: string,
  finish: string
): MeshPhysicalMaterial {
  return useMemo(() => {
    const base =
      SUBSTRATE_MATERIALS[substrate] ?? SUBSTRATE_MATERIALS["Metallic"];
    const mod = FINISH_MODIFIERS[finish] ?? {};

    return new MeshPhysicalMaterial({
      ...base,
      ...mod,
      // Finish roughness overrides substrate roughness
      roughness: mod.roughness ?? base.roughness ?? 0.5,
      side: DoubleSide,
    });
  }, [substrate, finish]);
}
