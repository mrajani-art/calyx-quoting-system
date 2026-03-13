"use client";

import { Suspense, useRef, useCallback, useEffect, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment, Center } from "@react-three/drei";
import type { BagVisualProps } from "../bag-svg/types";
import { BagModel } from "./BagModel";

/** Normalize scale so the bag fits comfortably in the camera view */
function computeScale(w: number, h: number, g: number): number {
  const maxDim = Math.max(w, h, g || 0.15);
  return 2.5 / maxDim;
}

interface Props {
  visualProps: BagVisualProps;
  onLoaded?: () => void;
}

function SceneContent({ visualProps, onLoaded }: Props) {
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const [autoRotate, setAutoRotate] = useState(true);

  const scale = computeScale(
    visualProps.width,
    visualProps.height,
    visualProps.gusset
  );

  const handleInteractionStart = useCallback(() => {
    setAutoRotate(false);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
  }, []);

  const handleInteractionEnd = useCallback(() => {
    timeoutRef.current = setTimeout(() => setAutoRotate(true), 3000);
  }, []);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  // Signal that scene is ready
  useEffect(() => {
    onLoaded?.();
  }, [onLoaded]);

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 5, 5]} intensity={0.8} />
      <directionalLight position={[-3, 2, -2]} intensity={0.3} />
      <Environment preset="studio" />

      {/* Camera controls */}
      <OrbitControls
        autoRotate={autoRotate}
        autoRotateSpeed={0.5}
        enablePan={false}
        minPolarAngle={Math.PI / 6}
        maxPolarAngle={Math.PI * 0.75}
        minDistance={3}
        maxDistance={10}
        onStart={handleInteractionStart}
        onEnd={handleInteractionEnd}
      />

      {/* The bag model, scaled and centered */}
      <Center>
        <group scale={[scale, scale, scale]}>
          <BagModel {...visualProps} />
        </group>
      </Center>
    </>
  );
}

export default function BagScene({ visualProps, onLoaded }: Props) {
  return (
    <Canvas
      camera={{ position: [0, 0.5, 5], fov: 40 }}
      style={{ width: "100%", height: "100%" }}
      gl={{ antialias: true, alpha: true }}
      dpr={[1, 2]}
    >
      <Suspense fallback={null}>
        <SceneContent visualProps={visualProps} onLoaded={onLoaded} />
      </Suspense>
    </Canvas>
  );
}
