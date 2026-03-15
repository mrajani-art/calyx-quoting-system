import {
  BagVisualProps,
  SVG_WIDTH,
  SUBSTRATE_FILLS,
  computeBagLayout,
} from "./types";
import {
  renderZipper,
  renderTearNotch,
  renderHolePunch,
  renderDimensionArrows,
  renderDefs,
} from "./features";

function buildBagPath(
  bagLeft: number,
  bagRight: number,
  bagTop: number,
  bagBottom: number,
  cornerR: number,
  gussetType: string,
  bagW: number
): string {
  const segments: string[] = [];

  // Top edge with optional rounded corners
  if (cornerR > 0) {
    segments.push(`M ${bagLeft} ${bagTop + cornerR}`);
    segments.push(`Q ${bagLeft} ${bagTop}, ${bagLeft + cornerR} ${bagTop}`);
    segments.push(`L ${bagRight - cornerR} ${bagTop}`);
    segments.push(`Q ${bagRight} ${bagTop}, ${bagRight} ${bagTop + cornerR}`);
  } else {
    segments.push(`M ${bagLeft} ${bagTop}`);
    segments.push(`L ${bagRight} ${bagTop}`);
  }

  // Bottom edge — small 45° chamfers for Plow Bottom / K Seal
  // Kept subtle (~5% of width) so the bag reads as a rectangle
  const cornerCut =
    gussetType === "Plow Bottom" || gussetType === "K Seal"
      ? Math.min(bagW * 0.05, 12)
      : 0;

  if (cornerCut > 0) {
    segments.push(`L ${bagRight} ${bagBottom - cornerCut}`);
    segments.push(`L ${bagRight - cornerCut} ${bagBottom}`);
    segments.push(`L ${bagLeft + cornerCut} ${bagBottom}`);
    segments.push(`L ${bagLeft} ${bagBottom - cornerCut}`);
  } else {
    segments.push(`L ${bagRight} ${bagBottom}`);
    segments.push(`L ${bagLeft} ${bagBottom}`);
  }

  // Left side back up
  if (cornerR > 0) {
    segments.push(`L ${bagLeft} ${bagTop + cornerR}`);
  } else {
    segments.push(`L ${bagLeft} ${bagTop}`);
  }

  segments.push("Z");
  return segments.join(" ");
}

export default function StandUpPouch(props: BagVisualProps) {
  const {
    width,
    height,
    gusset,
    gussetType,
    zipper,
    tearNotch,
    holePunch,
    corners,
    substrate,
    finish,
  } = props;

  // Compute dynamic layout — both width and height scale with real dimensions
  const { svgH, bagLeft, bagRight, bagTop, bagBottom, bagW, bagH, midX } =
    computeBagLayout(width, height);

  const cornerR = corners === "Rounded" ? 8 : 0;

  // Gusset depth (for dimension arrows only)
  const gussetDepth =
    gussetType === "None"
      ? 0
      : Math.min((gusset / height) * bagH * 0.35, 30);
  const gussetStartY = bagBottom - gussetDepth;

  // Build outline path
  const bagPath = buildBagPath(
    bagLeft,
    bagRight,
    bagTop,
    bagBottom,
    cornerR,
    gussetType,
    bagW
  );

  // Substrate fills
  const fills = SUBSTRATE_FILLS[substrate] || SUBSTRATE_FILLS["Metallic"];

  // Feature positions
  const zipperY = bagTop + 20;
  const tearNotchY = bagTop + 35;
  const holePunchCY = bagTop + 8;

  // 45° corner cut size for K Seal skirt band
  const cornerCut =
    gussetType === "Plow Bottom" || gussetType === "K Seal"
      ? Math.min(bagW * 0.05, 12)
      : 0;

  return (
    <svg
      viewBox={`0 0 ${SVG_WIDTH} ${svgH}`}
      xmlns="http://www.w3.org/2000/svg"
      className="w-full h-auto"
      role="img"
      aria-label="Stand-up pouch diagram"
    >
      {renderDefs(fills.start, fills.end, finish)}

      {/* Main bag body */}
      <path
        d={bagPath}
        fill="url(#substrate-fill)"
        fillOpacity={fills.opacity}
        stroke="#9CA3AF"
        strokeWidth={1.5}
        strokeLinejoin="round"
        filter={
          finish === "Soft Touch" ? "url(#soft-touch-texture)" : undefined
        }
      />

      {/* K Seal skirt seal — lighter band at the bottom matching the angled shape */}
      {gussetType === "K Seal" && cornerCut > 0 && (() => {
        const bandH = 12;
        const skirtPath = [
          `M ${bagRight} ${bagBottom - cornerCut}`,
          `L ${bagRight - cornerCut} ${bagBottom}`,
          `L ${bagLeft + cornerCut} ${bagBottom}`,
          `L ${bagLeft} ${bagBottom - cornerCut}`,
          `L ${bagLeft} ${bagBottom - cornerCut - bandH}`,
          `L ${bagLeft + cornerCut + bandH * 0.7} ${bagBottom - bandH}`,
          `L ${bagRight - cornerCut - bandH * 0.7} ${bagBottom - bandH}`,
          `L ${bagRight} ${bagBottom - cornerCut - bandH}`,
          `Z`,
        ].join(" ");
        return (
          <path
            d={skirtPath}
            fill="#D4D4D4"
            fillOpacity={0.45}
            stroke="none"
          />
        );
      })()}

      {/* Gloss finish overlay */}
      {finish === "Gloss" && (
        <path d={bagPath} fill="url(#gloss-sheen)" pointerEvents="none" />
      )}

      {/* Features */}
      {renderZipper(bagLeft, bagRight, zipperY, zipper)}
      {tearNotch === "Standard" &&
        renderTearNotch(bagLeft, bagRight, tearNotchY)}
      {holePunch !== "None" && renderHolePunch(midX, holePunchCY, holePunch)}

      {/* Dimension arrows */}
      {renderDimensionArrows(
        bagLeft,
        bagRight,
        bagTop,
        bagBottom,
        width,
        height,
        gusset,
        gussetType !== "None" ? gussetStartY : undefined
      )}
    </svg>
  );
}
