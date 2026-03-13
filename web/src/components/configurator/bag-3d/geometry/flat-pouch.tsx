"use client";

import { useMemo } from "react";
import { ExtrudeGeometry } from "three";
import { buildPouchShape } from "./pouch-shape";
import type { BagVisualProps } from "../../bag-svg/types";

interface Props {
  visualProps: BagVisualProps;
}

export function FlatPouchGeometry({ visualProps }: Props) {
  const geometry = useMemo(() => {
    const { shape, extrudeDepth } = buildPouchShape(visualProps);

    const geo = new ExtrudeGeometry(shape, {
      depth: extrudeDepth,
      bevelEnabled: true,
      bevelThickness: 0.01,
      bevelSize: 0.01,
      bevelSegments: 2,
      curveSegments: 12,
    });

    geo.center();
    geo.computeVertexNormals();

    return geo;
  }, [visualProps]);

  return <primitive object={geometry} attach="geometry" />;
}
