"use client";

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
  else if (props.holePunch === "Euro Slot") badges.push("Euro Slot");
  if (props.corners === "Rounded") badges.push("Rounded");
  if (props.finish !== "None" && props.finish !== "Matte")
    badges.push(props.finish);
  return badges;
}

function formatDims(w: number, h: number, g: number): string {
  if (g > 0) return `${w}" W × ${h}" H × ${g}" G`;
  return `${w}" W × ${h}" H`;
}

export default function BagPreview({ compact = false, ...visualProps }: Props) {
  const { sealType, width, height, gusset, substrate } = visualProps;
  const badges = featureBadges(visualProps);

  const isStandUpPouch = sealType === "Stand Up Pouch";

  return (
    <div className={compact ? "" : "space-y-3"}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-90">Preview</h4>
        <span className="text-xs text-gray-60">
          {isStandUpPouch ? "Stand Up Pouch" : sealType}
        </span>
      </div>

      {/* SVG container — fixed aspect so layout doesn't shift */}
      <div className="flex items-center justify-center rounded-lg border border-gray-10 bg-gray-5 p-4">
        <div className={compact ? "w-40" : "w-full max-w-[200px]"}>
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
