"use client";

import { useRef } from "react";
import type { Mesh } from "three";
import type { BagVisualProps } from "../bag-svg/types";
import { useBagMaterial } from "./materials";
import { MIN_DEPTH } from "./types";
import { StandUpPouchGeometry } from "./geometry/stand-up-pouch";
import { FlatPouchGeometry } from "./geometry/flat-pouch";
import { ZipperBand } from "./features/zipper-band";
import { TearNotches } from "./features/tear-notch";
import { HolePunch } from "./features/hole-punch";

export function BagModel(props: BagVisualProps) {
  const meshRef = useRef<Mesh>(null);
  const material = useBagMaterial(props.substrate, props.finish);

  const isStandUp = props.sealType === "Stand Up Pouch";
  const hasGusset =
    isStandUp && props.gussetType !== "None" && props.gusset > 0;
  const extrudeDepth = hasGusset ? props.gusset : MIN_DEPTH;

  return (
    <group>
      {/* Main bag body */}
      <mesh ref={meshRef} material={material}>
        {isStandUp ? (
          <StandUpPouchGeometry visualProps={props} />
        ) : (
          <FlatPouchGeometry visualProps={props} />
        )}
      </mesh>

      {/* Feature overlays */}
      {props.zipper !== "None" && (
        <ZipperBand
          width={props.width}
          height={props.height}
          depth={extrudeDepth}
          type={props.zipper}
        />
      )}

      {props.tearNotch === "Standard" && (
        <TearNotches
          width={props.width}
          height={props.height}
          depth={extrudeDepth}
        />
      )}

      {props.holePunch !== "None" && (
        <HolePunch
          height={props.height}
          depth={extrudeDepth}
          type={props.holePunch}
        />
      )}
    </group>
  );
}
