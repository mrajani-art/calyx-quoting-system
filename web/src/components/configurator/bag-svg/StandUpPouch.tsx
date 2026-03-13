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
  midX: number
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

  // Right side down to gusset start
  segments.push(`L ${bagRight} ${gussetStartY}`);

  // Bottom edge based on gusset type
  if (gussetType === "Plow Bottom") {
    segments.push(`Q ${bagRight} ${bagBottom}, ${midX} ${bagBottom}`);
    segments.push(`Q ${bagLeft} ${bagBottom}, ${bagLeft} ${gussetStartY}`);
  } else if (gussetType === "K Seal") {
    segments.push(`L ${midX} ${bagBottom}`);
    segments.push(`L ${bagLeft} ${gussetStartY}`);
  } else {
    // Flat bottom
    segments.push(`L ${bagRight} ${bagBottom}`);
    segments.push(`L ${bagLeft} ${bagBottom}`);
    segments.push(`L ${bagLeft} ${gussetStartY}`);
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
    midX
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

      {/* K Seal center crease line */}
      {gussetType === "K Seal" && (
        <line
          x1={midX}
          y1={bagBottom}
          x2={midX}
          y2={gussetStartY - 6}
          stroke="#9CA3AF"
          strokeWidth={0.75}
          strokeDasharray="3 2"
          opacity={0.5}
        />
      )}

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
