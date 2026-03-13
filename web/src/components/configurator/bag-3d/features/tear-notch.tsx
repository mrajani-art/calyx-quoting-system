"use client";

import { useMemo } from "react";
import { Shape, ExtrudeGeometry, MeshStandardMaterial } from "three";

interface TearNotchProps {
  width: number;
  height: number;
  depth: number;
}

export function TearNotches({ width, height, depth }: TearNotchProps) {
  const notchSize = 0.12;
  const yPos = height / 2 - 0.6; // slightly below zipper area
  const halfW = width / 2;

  // Create V-notch shape
  const notchShape = useMemo(() => {
    const s = new Shape();
    s.moveTo(0, -notchSize);
    s.lineTo(notchSize, 0);
    s.lineTo(0, notchSize);
    s.lineTo(0, -notchSize);
    return s;
  }, []);

  const geometry = useMemo(() => {
    const geo = new ExtrudeGeometry(notchShape, {
      depth: depth * 1.02,
      bevelEnabled: false,
    });
    return geo;
  }, [notchShape, depth]);

  const material = useMemo(
    () => new MeshStandardMaterial({ color: "#6B7280", metalness: 0.1, roughness: 0.5 }),
    []
  );

  return (
    <group>
      {/* Left notch */}
      <mesh geometry={geometry} material={material}
        position={[-halfW - 0.01, yPos, -depth / 2]} />
      {/* Right notch (mirrored) */}
      <mesh geometry={geometry} material={material}
        position={[halfW + 0.01, yPos, -depth / 2]}
        rotation={[0, Math.PI, 0]} />
    </group>
  );
}
