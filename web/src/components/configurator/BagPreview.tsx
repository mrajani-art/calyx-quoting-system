"use client";

import { useState, useCallback, useEffect } from "react";
import dynamic from "next/dynamic";
import StandUpPouch from "./bag-svg/StandUpPouch";
import FlatPouch from "./bag-svg/FlatPouch";
import type { BagVisualProps } from "./bag-svg/types";

// Dynamic import — only loaded client-side, never during SSR
const BagScene = dynamic(() => import("./bag-3d/BagScene"), {
  ssr: false,
  loading: () => null, // We show our own SVG fallback
});

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

/** Hook: true when viewport is >= 1024px (lg breakpoint) */
function useIsDesktop(): boolean {
  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    setIsDesktop(mq.matches);

    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  return isDesktop;
}

export default function BagPreview({ compact = false, ...visualProps }: Props) {
  const { sealType, width, height, gusset, substrate } = visualProps;
  const badges = featureBadges(visualProps);
  const isStandUpPouch = sealType === "Stand Up Pouch";

  const isDesktop = useIsDesktop();
  const [sceneReady, setSceneReady] = useState(false);
  const handleSceneLoaded = useCallback(() => setSceneReady(true), []);

  // Show SVG when: mobile, or desktop but 3D hasn't loaded yet
  const showSvg = !isDesktop || !sceneReady;
  const show3d = isDesktop;

  return (
    <div className={compact ? "" : "space-y-3"}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-90">Preview</h4>
        <span className="text-xs text-gray-60">
          {isStandUpPouch ? "Stand Up Pouch" : sealType}
          {show3d && sceneReady && (
            <span className="ml-1 text-gray-30">· 3D</span>
          )}
        </span>
      </div>

      {/* Preview container */}
      <div className="relative flex items-center justify-center rounded-lg border border-gray-10 bg-gray-5 p-4 min-h-[280px]">
        {/* SVG fallback: shown on mobile always, on desktop until 3D loads */}
        {showSvg && (
          <div className={compact ? "w-40" : "w-full max-w-[200px]"}>
            {isStandUpPouch ? (
              <StandUpPouch {...visualProps} />
            ) : (
              <FlatPouch {...visualProps} />
            )}
          </div>
        )}

        {/* 3D canvas: rendered on desktop, hidden until ready */}
        {show3d && (
          <div
            className={`absolute inset-0 ${
              sceneReady ? "" : "opacity-0 pointer-events-none"
            }`}
          >
            <BagScene
              visualProps={visualProps}
              onLoaded={handleSceneLoaded}
            />
          </div>
        )}
      </div>

      {/* Drag hint */}
      {show3d && sceneReady && (
        <p className="text-center text-[10px] text-gray-30">
          Drag to rotate · Scroll to zoom
        </p>
      )}

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
