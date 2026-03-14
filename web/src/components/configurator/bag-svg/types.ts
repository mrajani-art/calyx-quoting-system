export interface BagVisualProps {
  width: number;
  height: number;
  gusset: number;
  sealType: string;
  gussetType: string;
  zipper: string;
  tearNotch: string;
  holePunch: string;
  corners: string;
  substrate: string;
  finish: string;
  embellishment?: string;
}

// SVG layout constants
export const SVG_PADDING = 35;
export const MIN_SVG_HEIGHT = 200;
export const MAX_SVG_HEIGHT = 340;
export const SVG_WIDTH = 220;

// Substrate fill colors
export const SUBSTRATE_FILLS: Record<
  string,
  { start: string; end: string; opacity: number }
> = {
  Metallic: { start: "#D4D4D8", end: "#A1A1AA", opacity: 1 },
  Clear: { start: "#EFF6FF", end: "#DBEAFE", opacity: 0.4 },
  "White Metallic": { start: "#FFFFFF", end: "#F0F0FF", opacity: 1 },
  "High Barrier": { start: "#FAF9F6", end: "#F5F0EB", opacity: 1 },
};
