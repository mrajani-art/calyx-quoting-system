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

export default function FlatPouch(props: BagVisualProps) {
  const {
    width,
    height,
    sealType,
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

  const fills = SUBSTRATE_FILLS[substrate] ?? SUBSTRATE_FILLS["Metallic"];
  const cornerR = corners === "Rounded" ? 8 : 0;
  const sealInset = 5;

  return (
    <svg
      viewBox={`0 0 ${SVG_WIDTH} ${svgH}`}
      className="w-full h-auto"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Flat pouch diagram"
    >
      {renderDefs(fills.start, fills.end, finish)}

      {/* Main bag body */}
      <rect
        x={bagLeft}
        y={bagTop}
        width={bagW}
        height={bagH}
        rx={cornerR}
        ry={cornerR}
        fill="url(#substrate-fill)"
        fillOpacity={fills.opacity}
        stroke="#9CA3AF"
        strokeWidth={1.5}
        filter={
          finish === "Soft Touch" ? "url(#soft-touch-texture)" : undefined
        }
      />

      {/* Gloss finish overlay */}
      {finish === "Gloss" && (
        <rect
          x={bagLeft}
          y={bagTop}
          width={bagW}
          height={bagH}
          rx={cornerR}
          ry={cornerR}
          fill="url(#gloss-sheen)"
          pointerEvents="none"
        />
      )}

      {/* Seal lines */}
      {/* Left seal */}
      <line
        x1={bagLeft + sealInset}
        y1={bagTop + cornerR}
        x2={bagLeft + sealInset}
        y2={bagBottom - cornerR}
        stroke="#D4D4D8"
        strokeWidth={1}
        strokeDasharray="4 3"
      />
      {/* Right seal */}
      <line
        x1={bagRight - sealInset}
        y1={bagTop + cornerR}
        x2={bagRight - sealInset}
        y2={bagBottom - cornerR}
        stroke="#D4D4D8"
        strokeWidth={1}
        strokeDasharray="4 3"
      />
      {/* Bottom seal (3 Side Seal only) */}
      {sealType === "3 Side Seal" && (
        <line
          x1={bagLeft + cornerR}
          y1={bagBottom - sealInset}
          x2={bagRight - cornerR}
          y2={bagBottom - sealInset}
          stroke="#D4D4D8"
          strokeWidth={1}
          strokeDasharray="4 3"
        />
      )}

      {/* Features */}
      {renderZipper(bagLeft, bagRight, bagTop + 20, zipper)}
      {tearNotch === "Standard" &&
        renderTearNotch(bagLeft, bagRight, bagTop + 35)}
      {holePunch !== "None" && renderHolePunch(midX, bagTop + 8, holePunch)}

      {/* Dimension arrows (no gusset) */}
      {renderDimensionArrows(bagLeft, bagRight, bagTop, bagBottom, width, height, 0)}
    </svg>
  );
}
