"use client";

import { useMemo } from "react";
import { MeshStandardMaterial } from "three";

interface HolePunchProps {
  height: number;
  depth: number;
  type: string; // "Round" | "Euro Slot"
}

export function HolePunch({ height, depth, type }: HolePunchProps) {
  const yPos = height / 2 - 0.15; // near very top

  const holeMaterial = useMemo(
    () => new MeshStandardMaterial({ color: "#FFFFFF", metalness: 0, roughness: 0.9 }),
    []
  );
  const ringMaterial = useMemo(
    () => new MeshStandardMaterial({ color: "#9CA3AF", metalness: 0.2, roughness: 0.5 }),
    []
  );

  if (type === "Round") {
    return (
      <group position={[0, yPos, 0]}>
        {/* Hole cylinder */}
        <mesh material={holeMaterial} rotation={[Math.PI / 2, 0, 0]}>
          <cylinderGeometry args={[0.1, 0.1, depth * 1.1, 16]} />
        </mesh>
        {/* Ring on front face */}
        <mesh material={ringMaterial} position={[0, 0, depth / 2 + 0.005]}>
          <ringGeometry args={[0.08, 0.12, 16]} />
        </mesh>
        {/* Ring on back face */}
        <mesh material={ringMaterial} position={[0, 0, -depth / 2 - 0.005]} rotation={[0, Math.PI, 0]}>
          <ringGeometry args={[0.08, 0.12, 16]} />
        </mesh>
      </group>
    );
  }

  // Euro Slot
  return (
    <group position={[0, yPos, 0]}>
      <mesh material={holeMaterial} rotation={[Math.PI / 2, 0, 0]}>
        <capsuleGeometry args={[0.06, 0.2, 4, 12]} />
      </mesh>
    </group>
  );
}
