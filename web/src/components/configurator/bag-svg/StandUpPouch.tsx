import {
  BagVisualProps,
  SVG_PADDING,
  MIN_SVG_HEIGHT,
  MAX_SVG_HEIGHT,
  SVG_WIDTH,
  SUBSTRATE_FILLS,
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
  gussetStartY: number,
  midX: number,
  gussetDepth: number
): string {
  const segments: string[] = [];

  if (cornerR > 0) {
    segments.push(`M ${bagLeft} ${bagTop + cornerR}`);
    segments.push(`Q ${bagLeft} ${bagTop}, ${bagLeft + cornerR} ${bagTop}`);
    segments.push(`L ${bagRight - cornerR} ${bagTop}`);
    segments.push(`Q ${bagRight} ${bagTop}, ${bagRight} ${bagTop + cornerR}`);
  } else {
    segments.push(`M ${bagLeft} ${bagTop}`);
    segments.push(`L ${bagRight} ${bagTop}`);
  }

  // Bottom edge based on gusset type
  const cornerCut = Math.min(gussetDepth * 0.8, 18); // 45-degree corner size
  if (gussetType === "Plow Bottom" || gussetType === "K Seal") {
    // 45-degree angled corner seals at the bottom
    segments.push(`L ${bagRight} ${bagBottom - cornerCut}`);
    segments.push(`L ${bagRight - cornerCut} ${bagBottom}`);
    segments.push(`L ${bagLeft + cornerCut} ${bagBottom}`);
    segments.push(`L ${bagLeft} ${bagBottom - cornerCut}`);
  } else {
    // No gusset — straight sides to flat bottom
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

  // Compute SVG layout
  const bagLeft = SVG_PADDING;
  const bagRight = SVG_WIDTH - SVG_PADDING;
  const bagWidth = bagRight - bagLeft;
  const aspectRatio = width / height;
  const rawH = bagWidth / aspectRatio + 50;
  const svgH = Math.min(MAX_SVG_HEIGHT, Math.max(MIN_SVG_HEIGHT, rawH));
  const bagTop = 20;
  const bagBottom = svgH - 30;
  const midX = (bagLeft + bagRight) / 2;
  const cornerR = corners === "Rounded" ? 8 : 0;

  // Gusset depth
  const gussetDepth =
    gussetType === "None"
      ? 0
      : Math.min((gusset / height) * (bagBottom - bagTop) * 0.35, 30);
  const gussetStartY = bagBottom - gussetDepth;

  // Build outline path
  const bagPath = buildBagPath(
    bagLeft,
    bagRight,
    bagTop,
    bagBottom,
    cornerR,
    gussetType,
    gussetStartY,
    midX,
    gussetDepth
  );

  // Substrate fills
  const fills = SUBSTRATE_FILLS[substrate] || SUBSTRATE_FILLS["Metallic"];

  // Feature positions
  const zipperY = bagTop + 20;
  const tearNotchY = bagTop + 35;
  const holePunchCY = bagTop + 8;

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
      {gussetType === "K Seal" && gussetDepth > 0 && (() => {
        const cc = Math.min(gussetDepth * 0.8, 18);
        const bandH = 12;
        const skirtPath = [
          `M ${bagRight} ${bagBottom - cc}`,
          `L ${bagRight - cc} ${bagBottom}`,
          `L ${bagLeft + cc} ${bagBottom}`,
          `L ${bagLeft} ${bagBottom - cc}`,
          `L ${bagLeft} ${bagBottom - cc - bandH}`,
          `L ${bagLeft + cc + bandH * 0.7} ${bagBottom - bandH}`,
          `L ${bagRight - cc - bandH * 0.7} ${bagBottom - bandH}`,
          `L ${bagRight} ${bagBottom - cc - bandH}`,
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
