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

/** Always a full rectangle — optional rounded top corners only */
function buildBagPath(
  bagLeft: number,
  bagRight: number,
  bagTop: number,
  bagBottom: number,
  cornerR: number
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

  // Straight sides and flat bottom — always a full rectangle
  segments.push(`L ${bagRight} ${bagBottom}`);
  segments.push(`L ${bagLeft} ${bagBottom}`);

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
  } = props;

  // Compute dynamic layout — both width and height scale with real dimensions
  const { svgH, bagLeft, bagRight, bagTop, bagBottom, bagW, bagH, midX } =
    computeBagLayout(width, height);

  const cornerR = corners === "Rounded" ? 8 : 0;

  // K Seal / Plow Bottom triangle size — proportional to gusset depth
  const triSize =
    gussetType === "None"
      ? 0
      : Math.min((gusset / height) * bagH * 0.4, bagH * 0.2, 40);
  const gussetStartY = bagBottom - triSize;

  // Build outline path — always a full rectangle
  const bagPath = buildBagPath(bagLeft, bagRight, bagTop, bagBottom, cornerR);

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
      {renderDefs(fills.start, fills.end)}

      {/* Main bag body */}
      <path
        d={bagPath}
        fill="url(#substrate-fill)"
        fillOpacity={fills.opacity}
        stroke="#9CA3AF"
        strokeWidth={1.5}
        strokeLinejoin="round"
      />

      {/* K Seal / Plow Bottom — triangular corner folds inside the bag */}
      {(gussetType === "K Seal" || gussetType === "Plow Bottom") &&
        triSize > 0 && (
          <g>
            {/* Left triangle fold */}
            <path
              d={`M ${bagLeft} ${bagBottom} L ${bagLeft + triSize} ${bagBottom} L ${bagLeft} ${bagBottom - triSize} Z`}
              fill="#D4D4D4"
              fillOpacity={0.3}
              stroke="#9CA3AF"
              strokeWidth={1}
              strokeLinejoin="round"
            />
            {/* Right triangle fold */}
            <path
              d={`M ${bagRight} ${bagBottom} L ${bagRight - triSize} ${bagBottom} L ${bagRight} ${bagBottom - triSize} Z`}
              fill="#D4D4D4"
              fillOpacity={0.3}
              stroke="#9CA3AF"
              strokeWidth={1}
              strokeLinejoin="round"
            />
            {/* Skirt seal line — K Seal only */}
            {gussetType === "K Seal" && (
              <line
                x1={bagLeft + triSize}
                y1={bagBottom - triSize * 0.2}
                x2={bagRight - triSize}
                y2={bagBottom - triSize * 0.2}
                stroke="#9CA3AF"
                strokeWidth={1}
              />
            )}
          </g>
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
