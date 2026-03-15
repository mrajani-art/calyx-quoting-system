"use client";

import { useState, useRef, useCallback } from "react";
import StandUpPouch from "./bag-svg/StandUpPouch";
import FlatPouch from "./bag-svg/FlatPouch";
import type { BagVisualProps } from "./bag-svg/types";

interface Props extends BagVisualProps {
  compact?: boolean;
}

function featureBadges(props: BagVisualProps): string[] {
  const badges: string[] = [];
  if (props.zipper === "Child-Resistant") badges.push("CR Zipper");
  else if (props.zipper === "Standard") badges.push("Zipper");
  if (props.tearNotch === "Standard") badges.push("Tear Notch");
  if (props.holePunch === "Round") badges.push("Round Punch");
  else if (props.holePunch === "Euro Slot") badges.push("Sombrero");
  if (props.corners === "Rounded") badges.push("Rounded");
  if (props.finish !== "None" && props.finish !== "Matte")
    badges.push(props.finish);
  return badges;
}

function formatDims(w: number, h: number, g: number): string {
  if (g > 0) return `${w}" W × ${h}" H × ${g}" G`;
  return `${w}" W × ${h}" H`;
}

/** Clamp a value between min and max */
function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val));
}

export default function BagPreview({ compact = false, ...visualProps }: Props) {
  const { sealType, width, height, gusset, substrate } = visualProps;
  const badges = featureBadges(visualProps);
  const isStandUpPouch = sealType === "Stand Up Pouch";

  // Perspective tilt state
  const containerRef = useRef<HTMLDivElement>(null);
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const [isHovering, setIsHovering] = useState(false);

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      const el = containerRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      // Normalize mouse position to -1..1 from center
      const nx = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      const ny = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
      // Clamp to ±12 degrees
      setTilt({
        x: clamp(-ny * 12, -12, 12), // tilt around X axis (vertical mouse → pitch)
        y: clamp(nx * 12, -12, 12),  // tilt around Y axis (horizontal mouse → yaw)
      });
    },
    []
  );

  const handleMouseEnter = useCallback(() => setIsHovering(true), []);
  const handleMouseLeave = useCallback(() => {
    setIsHovering(false);
    setTilt({ x: 0, y: 0 });
  }, []);

  return (
    <div className={compact ? "" : "space-y-3"}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-90">Preview</h4>
        <span className="text-xs text-gray-60">
          {isStandUpPouch ? "Stand Up Pouch" : sealType}
        </span>
      </div>

      {/* SVG container with perspective tilt */}
      <div
        ref={containerRef}
        onMouseMove={handleMouseMove}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        className="flex items-center justify-center rounded-lg border border-gray-10 bg-gray-5 p-4 cursor-grab active:cursor-grabbing"
        style={{ perspective: "600px" }}
      >
        <div
          className={compact ? "w-48" : "w-full max-w-[300px]"}
          style={{
            transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
            transition: isHovering
              ? "transform 0.08s ease-out"
              : "transform 0.5s cubic-bezier(0.22, 1, 0.36, 1)",
            transformStyle: "preserve-3d",
          }}
        >
          {isStandUpPouch ? (
            <StandUpPouch {...visualProps} />
          ) : (
            <FlatPouch {...visualProps} />
          )}
        </div>
      </div>

      {/* Dimension label */}
      <p className="text-center text-xs font-medium text-gray-60">
        {formatDims(width, height, gusset)}
        <span className="mx-1.5 text-gray-30">·</span>
        {substrate}
      </p>

      {/* Feature badges */}
      {badges.length > 0 && (
        <div className="flex flex-wrap justify-center gap-1.5">
          {badges.map((badge) => (
            <span
              key={badge}
              className="rounded-full bg-cloud-blue px-2 py-0.5 text-[10px] font-medium text-calyx-blue"
            >
              {badge}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
