"use client";

import { useMemo } from "react";
import { ExtrudeGeometry } from "three";
import { buildPouchShape } from "./pouch-shape";
import type { BagVisualProps } from "../../bag-svg/types";

interface Props {
  visualProps: BagVisualProps;
}

export function StandUpPouchGeometry({ visualProps }: Props) {
  const geometry = useMemo(() => {
    const { shape, extrudeDepth } = buildPouchShape(visualProps);

    const geo = new ExtrudeGeometry(shape, {
      depth: extrudeDepth,
      bevelEnabled: true,
      bevelThickness: 0.02,
      bevelSize: 0.02,
      bevelSegments: 3,
      curveSegments: 24,
    });

    geo.center();
    geo.computeVertexNormals();

    return geo;
  }, [visualProps]);

  return <primitive object={geometry} attach="geometry" />;
}
