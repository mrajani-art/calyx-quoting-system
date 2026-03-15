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
export const SVG_WIDTH = 330;
const SIDE_PAD = 50;
const TOP_PAD = 25;
const BOT_PAD = 45;
const MAX_BAG_W = SVG_WIDTH - 2 * SIDE_PAD; // 230
const MAX_BAG_H = 350;

/**
 * Compute dynamic bag layout based on real dimensions.
 * Both width AND height of the drawn bag vary proportionally,
 * so a 2.5"×5" vape bag looks visibly narrower than a 12"×10" exit bag.
 */
export function computeBagLayout(widthInches: number, heightInches: number) {
  const aspectRatio = widthInches / (heightInches || 1);

  let bagW: number;
  let bagH: number;

  if (aspectRatio >= MAX_BAG_W / MAX_BAG_H) {
    // Width-constrained — scale height down
    bagW = MAX_BAG_W;
    bagH = MAX_BAG_W / aspectRatio;
  } else {
    // Height-constrained — scale width down
    bagH = MAX_BAG_H;
    bagW = MAX_BAG_H * aspectRatio;
  }

  const svgH = bagH + TOP_PAD + BOT_PAD;
  const bagLeft = (SVG_WIDTH - bagW) / 2;
  const bagRight = bagLeft + bagW;
  const bagTop = TOP_PAD;
  const bagBottom = TOP_PAD + bagH;
  const midX = SVG_WIDTH / 2;

  return { svgH, bagLeft, bagRight, bagTop, bagBottom, bagW, bagH, midX };
}

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
