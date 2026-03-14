import React from "react";

/** Zipper band near the top of the bag */
export function renderZipper(
  x1: number,
  x2: number,
  y: number,
  type: string
): React.ReactNode {
  const isCR = type === "Child-Resistant";
  return (
    <g key="zipper">
      <rect
        x={x1}
        y={y - 6}
        width={x2 - x1}
        height={12}
        fill="#E5E5E5"
        fillOpacity={0.5}
        stroke="none"
      />
      <line
        x1={x1 + 4}
        y1={y}
        x2={x2 - 4}
        y2={y}
        stroke="#9CA3AF"
        strokeWidth={isCR ? 1.5 : 1}
        strokeDasharray={isCR ? "6 3" : "4 2"}
      />
      {isCR && (
        <line
          x1={x1 + 4}
          y1={y + 3}
          x2={x2 - 4}
          y2={y + 3}
          stroke="#9CA3AF"
          strokeWidth={1}
          strokeDasharray="6 3"
        />
      )}
    </g>
  );
}

/** V-shaped tear notches on left and right edges */
export function renderTearNotch(
  leftX: number,
  rightX: number,
  y: number
): React.ReactNode {
  const size = 5;
  return (
    <g key="tear-notch">
      <path
        d={`M ${leftX} ${y - size} L ${leftX + size} ${y} L ${leftX} ${y + size}`}
        fill="none"
        stroke="#6B7280"
        strokeWidth={1.5}
      />
      <path
        d={`M ${rightX} ${y - size} L ${rightX - size} ${y} L ${rightX} ${y + size}`}
        fill="none"
        stroke="#6B7280"
        strokeWidth={1.5}
      />
    </g>
  );
}

/** Hole punch at top center of the bag */
export function renderHolePunch(
  cx: number,
  cy: number,
  type: string
): React.ReactNode {
  if (type === "Round") {
    return (
      <circle
        key="hole-punch"
        cx={cx}
        cy={cy}
        r={5}
        fill="white"
        stroke="#9CA3AF"
        strokeWidth={1}
      />
    );
  }
  // Sombrero (inverted T shape — wide base slot with narrow top slot)
  return (
    <g key="hole-punch">
      {/* Wide base slot */}
      <rect
        x={cx - 8}
        y={cy - 2}
        width={16}
        height={5}
        rx={1.5}
        fill="white"
        stroke="#9CA3AF"
        strokeWidth={1}
      />
      {/* Narrow top slot */}
      <rect
        x={cx - 2.5}
        y={cy - 7}
        width={5}
        height={6}
        rx={1.5}
        fill="white"
        stroke="#9CA3AF"
        strokeWidth={1}
      />
      {/* Cover the seam between the two rects */}
      <rect
        x={cx - 2}
        y={cy - 2.5}
        width={4}
        height={3}
        fill="white"
        stroke="none"
      />
    </g>
  );
}

/** Dimension arrows with labels outside the bag */
export function renderDimensionArrows(
  bagLeft: number,
  bagRight: number,
  bagTop: number,
  bagBottom: number,
  widthInches: number,
  heightInches: number,
  gussetInches: number,
  gussetBottomY?: number
): React.ReactNode {
  const arrowOffset = 14;
  const ah = 3; // arrowhead size
  const midX = (bagLeft + bagRight) / 2;

  return (
    <g key="dimensions" className="select-none">
      {/* Width arrow (bottom) */}
      <line
        x1={bagLeft}
        y1={bagBottom + arrowOffset}
        x2={bagRight}
        y2={bagBottom + arrowOffset}
        stroke="#9CA3AF"
        strokeWidth={0.75}
      />
      <path
        d={`M ${bagLeft} ${bagBottom + arrowOffset} l ${ah} ${-ah} M ${bagLeft} ${bagBottom + arrowOffset} l ${ah} ${ah}`}
        stroke="#9CA3AF"
        strokeWidth={0.75}
        fill="none"
      />
      <path
        d={`M ${bagRight} ${bagBottom + arrowOffset} l ${-ah} ${-ah} M ${bagRight} ${bagBottom + arrowOffset} l ${-ah} ${ah}`}
        stroke="#9CA3AF"
        strokeWidth={0.75}
        fill="none"
      />
      <text
        x={midX}
        y={bagBottom + arrowOffset + 11}
        textAnchor="middle"
        fontSize="9"
        fill="#6B7280"
        fontFamily="system-ui"
      >
        {widthInches}&quot;
      </text>

      {/* Height arrow (right side) */}
      <line
        x1={bagRight + arrowOffset}
        y1={bagTop}
        x2={bagRight + arrowOffset}
        y2={bagBottom}
        stroke="#9CA3AF"
        strokeWidth={0.75}
      />
      <path
        d={`M ${bagRight + arrowOffset} ${bagTop} l ${-ah} ${ah} M ${bagRight + arrowOffset} ${bagTop} l ${ah} ${ah}`}
        stroke="#9CA3AF"
        strokeWidth={0.75}
        fill="none"
      />
      <path
        d={`M ${bagRight + arrowOffset} ${bagBottom} l ${-ah} ${-ah} M ${bagRight + arrowOffset} ${bagBottom} l ${ah} ${-ah}`}
        stroke="#9CA3AF"
        strokeWidth={0.75}
        fill="none"
      />
      <text
        x={bagRight + arrowOffset + 4}
        y={(bagTop + bagBottom) / 2}
        textAnchor="start"
        fontSize="9"
        fill="#6B7280"
        fontFamily="system-ui"
        dominantBaseline="central"
      >
        {heightInches}&quot;
      </text>

      {/* Gusset depth label (only if > 0) */}
      {gussetInches > 0 && gussetBottomY && (
        <g>
          <line
            x1={bagLeft - arrowOffset}
            y1={gussetBottomY}
            x2={bagLeft - arrowOffset}
            y2={bagBottom}
            stroke="#9CA3AF"
            strokeWidth={0.75}
            strokeDasharray="3 2"
          />
          <text
            x={bagLeft - arrowOffset}
            y={bagBottom + 11}
            textAnchor="middle"
            fontSize="8"
            fill="#6B7280"
            fontFamily="system-ui"
          >
            {gussetInches}&quot; G
          </text>
        </g>
      )}
    </g>
  );
}

/** SVG defs for substrate gradient and finish overlay */
export function renderDefs(
  gradientStart: string,
  gradientEnd: string,
  finish: string
): React.ReactNode {
  return (
    <defs>
      <linearGradient id="substrate-fill" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor={gradientStart} />
        <stop offset="100%" stopColor={gradientEnd} />
      </linearGradient>

      {finish === "Gloss" && (
        <linearGradient id="gloss-sheen" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="white" stopOpacity={0.25} />
          <stop offset="40%" stopColor="white" stopOpacity={0} />
          <stop offset="60%" stopColor="white" stopOpacity={0} />
          <stop offset="100%" stopColor="white" stopOpacity={0.15} />
        </linearGradient>
      )}

      {finish === "Soft Touch" && (
        <filter id="soft-touch-texture">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.9"
            numOctaves={4}
            result="noise"
          />
          <feColorMatrix
            type="saturate"
            values="0"
            in="noise"
            result="gray-noise"
          />
          <feBlend in="SourceGraphic" in2="gray-noise" mode="soft-light" />
        </filter>
      )}
    </defs>
  );
}
