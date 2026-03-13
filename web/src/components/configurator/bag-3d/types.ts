import type { MeshPhysicalMaterialParameters } from "three";

/** Map substrate name → base PBR material properties */
export const SUBSTRATE_MATERIALS: Record<
  string,
  MeshPhysicalMaterialParameters
> = {
  Metallic: {
    color: "#C0C0C8",
    metalness: 0.9,
    roughness: 0.2,
    clearcoat: 0.1,
  },
  Clear: {
    color: "#E8F0FE",
    metalness: 0.0,
    roughness: 0.1,
    transmission: 0.85,
    transparent: true,
    opacity: 0.4,
    ior: 1.45,
    thickness: 0.5,
  },
  "White Metallic": {
    color: "#F0F0FF",
    metalness: 0.5,
    roughness: 0.3,
    clearcoat: 0.05,
  },
  "High Barrier": {
    color: "#FAF5EE",
    metalness: 0.0,
    roughness: 0.5,
  },
};

/** Finish modifiers applied on top of substrate base */
export const FINISH_MODIFIERS: Record<
  string,
  Partial<MeshPhysicalMaterialParameters>
> = {
  Gloss: { roughness: 0.05, clearcoat: 0.3, clearcoatRoughness: 0.05 },
  Matte: { roughness: 0.8, clearcoat: 0.0 },
  "Soft Touch": {
    roughness: 0.9,
    clearcoat: 0.4,
    clearcoatRoughness: 0.6,
  },
  None: {},
};

/** Minimum extrusion depth for flat pouches with no gusset (inches) */
export const MIN_DEPTH = 0.15;
