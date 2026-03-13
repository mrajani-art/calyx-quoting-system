"use client";

import { useMemo } from "react";
import { MeshStandardMaterial } from "three";

interface ZipperProps {
  width: number;   // bag width in inches
  height: number;  // bag height in inches
  depth: number;   // extrusion depth (gusset or MIN_DEPTH)
  type: string;    // "Standard" | "Child-Resistant"
}

export function ZipperBand({ width, height, depth, type }: ZipperProps) {
  const isCR = type === "Child-Resistant";
  const bandHeight = isCR ? 0.25 : 0.12;
  // Position near top of bag
  const yPos = height / 2 - 0.4;

  // Material: light gray, slightly metallic
  const material = useMemo(() => new MeshStandardMaterial({
    color: "#D4D4D8", metalness: 0.3, roughness: 0.6, transparent: true, opacity: 0.7,
  }), []);

  return (
    <group position={[0, yPos, 0]}>
      <mesh material={material}>
        <boxGeometry args={[width * 0.92, bandHeight, depth * 1.02]} />
      </mesh>
      {/* CR double track */}
      {isCR && (
        <mesh position={[0, -0.08, 0]} material={material}>
          <boxGeometry args={[width * 0.92, 0.04, depth * 1.02]} />
        </mesh>
      )}
    </group>
  );
}
