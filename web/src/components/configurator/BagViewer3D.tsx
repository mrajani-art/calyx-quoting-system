"use client";

import { Suspense, useRef, useState, useCallback, useEffect, useMemo } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, useGLTF, Environment, ContactShadows } from "@react-three/drei";
import * as THREE from "three";
import type { BagVisualProps } from "./bag-svg/types";

// ── Model path mapping ────────────────────────────────────────
function getModelPath(sealType: string, gussetType: string): string {
  if (sealType === "Stand Up Pouch") {
    return gussetType === "Plow Bottom"
      ? "/models/standup-plow.glb"
      : "/models/standup-kseal.glb";
  }
  if (sealType === "2 Side Seal") return "/models/flat-2side.glb";
  return "/models/flat-3side.glb";
}

// ── Material properties from config ───────────────────────────
interface MaterialConfig {
  color: THREE.Color;
  metalness: number;
  roughness: number;
  opacity: number;
  transparent: boolean;
  clearcoat: number;
  clearcoatRoughness: number;
  transmission: number;
  ior: number;
}

function getMaterialConfig(substrate: string, finish: string): MaterialConfig {
  // Substrate determines base color and metalness
  const substrateMap: Record<string, { color: [number, number, number]; metalness: number; opacity: number; transmission: number }> = {
    Metallic: { color: [0.38, 0.38, 0.42], metalness: 0.92, opacity: 1, transmission: 0 },
    "White Metallic": { color: [0.78, 0.78, 0.84], metalness: 0.55, opacity: 1, transmission: 0 },
    "High Barrier": { color: [0.92, 0.95, 0.97], metalness: 0, opacity: 0.4, transmission: 0.6 },
    Clear: { color: [0.90, 0.94, 1.0], metalness: 0, opacity: 0.25, transmission: 0.75 },
  };

  // Finish determines roughness and clearcoat
  const finishMap: Record<string, { roughness: number; clearcoat: number; clearcoatRoughness: number }> = {
    Matte: { roughness: 0.65, clearcoat: 0, clearcoatRoughness: 0 },
    "Soft Touch": { roughness: 0.82, clearcoat: 0, clearcoatRoughness: 0 },
    Gloss: { roughness: 0.05, clearcoat: 0.8, clearcoatRoughness: 0.02 },
  };

  const sub = substrateMap[substrate] || substrateMap.Metallic;
  const fin = finishMap[finish] || finishMap.Matte;

  return {
    color: new THREE.Color(...sub.color),
    metalness: sub.metalness,
    roughness: fin.roughness,
    opacity: sub.opacity,
    transparent: sub.opacity < 1,
    clearcoat: fin.clearcoat,
    clearcoatRoughness: fin.clearcoatRoughness,
    transmission: sub.transmission,
    ior: 1.45,
  };
}

// ── Bag mesh component ────────────────────────────────────────
function BagModel({
  modelPath,
  materialConfig,
  artworkUrl,
}: {
  modelPath: string;
  materialConfig: MaterialConfig;
  artworkUrl?: string;
}) {
  const { scene } = useGLTF(modelPath);
  const groupRef = useRef<THREE.Group>(null);
  const artworkTexture = useRef<THREE.Texture | null>(null);

  // Load artwork texture if provided
  useEffect(() => {
    if (artworkUrl) {
      const loader = new THREE.TextureLoader();
      loader.load(artworkUrl, (tex) => {
        tex.flipY = false;
        tex.colorSpace = THREE.SRGBColorSpace;
        artworkTexture.current = tex;
      });
    } else {
      artworkTexture.current = null;
    }
  }, [artworkUrl]);

  // Clone the scene so we can modify materials without affecting cache
  const clonedScene = useMemo(() => {
    const clone = scene.clone(true);
    return clone;
  }, [scene]);

  // Apply materials dynamically
  useEffect(() => {
    clonedScene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        const isBagBody = child.name === "Bag" || child.name.includes("Bag");
        const isZipper = child.name.includes("Zipper");
        const isSeal = child.name.includes("Seal");

        if (isBagBody) {
          const mat = new THREE.MeshPhysicalMaterial({
            color: materialConfig.color,
            metalness: materialConfig.metalness,
            roughness: materialConfig.roughness,
            opacity: materialConfig.opacity,
            transparent: materialConfig.transparent,
            clearcoat: materialConfig.clearcoat,
            clearcoatRoughness: materialConfig.clearcoatRoughness,
            transmission: materialConfig.transmission,
            ior: materialConfig.ior,
            envMapIntensity: 1.2,
            side: THREE.DoubleSide,
          });

          // Apply artwork texture if available
          if (artworkTexture.current) {
            mat.map = artworkTexture.current;
            mat.needsUpdate = true;
          }

          child.material = mat;
        } else if (isZipper) {
          child.material = new THREE.MeshPhysicalMaterial({
            color: new THREE.Color(0.75, 0.75, 0.75),
            metalness: 0.15,
            roughness: 0.35,
            envMapIntensity: 0.8,
          });
        } else if (isSeal) {
          child.material = new THREE.MeshPhysicalMaterial({
            color: new THREE.Color(0.85, 0.85, 0.87),
            metalness: 0,
            roughness: 0.6,
            opacity: 0.25,
            transparent: true,
          });
        }
      }
    });
  }, [clonedScene, materialConfig, artworkUrl]);

  // Slight initial rotation to show 3/4 view
  useEffect(() => {
    if (groupRef.current) {
      groupRef.current.rotation.y = 0.3; // 3/4 angle
    }
  }, []);

  return (
    <group ref={groupRef}>
      <primitive object={clonedScene} />
    </group>
  );
}

// ── Scene setup ───────────────────────────────────────────────
function Scene({
  modelPath,
  materialConfig,
  artworkUrl,
}: {
  modelPath: string;
  materialConfig: MaterialConfig;
  artworkUrl?: string;
}) {
  const controlsRef = useRef<any>(null);

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.2} />
      <directionalLight position={[3, 4, 2]} intensity={0.8} color="#fff8f0" />
      <directionalLight position={[-2, 3, -1]} intensity={0.3} color="#f0f4ff" />
      <directionalLight position={[0, -1, 3]} intensity={0.15} />

      {/* Environment for realistic reflections — reduced intensity */}
      <Environment preset="studio" environmentIntensity={0.6} />

      {/* Bag model */}
      <BagModel
        modelPath={modelPath}
        materialConfig={materialConfig}
        artworkUrl={artworkUrl}
      />

      {/* Shadow under bag */}
      <ContactShadows
        position={[0, -0.01, 0]}
        opacity={0.4}
        scale={0.5}
        blur={2}
        far={0.5}
      />

      {/* Orbit controls — user can rotate/zoom */}
      <OrbitControls
        ref={controlsRef}
        enablePan={false}
        enableZoom={true}
        minDistance={0.25}
        maxDistance={0.8}
        minPolarAngle={Math.PI * 0.2}
        maxPolarAngle={Math.PI * 0.65}
        autoRotate={false}
        target={[0, 0.09, 0]}
      />
    </>
  );
}

// ── Loading spinner ───────────────────────────────────────────
function LoadingFallback() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-2">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-gray-30 border-t-calyx-blue" />
        <span className="text-xs text-gray-60">Loading 3D preview…</span>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────
interface BagViewer3DProps extends BagVisualProps {
  compact?: boolean;
  artworkUrl?: string;
  onArtworkUpload?: (url: string) => void;
}

export default function BagViewer3D({
  compact = false,
  artworkUrl,
  onArtworkUpload,
  ...visualProps
}: BagViewer3DProps) {
  const { sealType, gussetType, substrate, finish, width, height, gusset } = visualProps;
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [localArtworkUrl, setLocalArtworkUrl] = useState<string | undefined>(artworkUrl);

  const modelPath = getModelPath(sealType, gussetType);
  const materialConfig = getMaterialConfig(substrate, finish);

  // Handle artwork file upload
  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      const url = URL.createObjectURL(file);
      setLocalArtworkUrl(url);
      onArtworkUpload?.(url);
    },
    [onArtworkUpload]
  );

  const handleRemoveArtwork = useCallback(() => {
    if (localArtworkUrl) {
      URL.revokeObjectURL(localArtworkUrl);
    }
    setLocalArtworkUrl(undefined);
    onArtworkUpload?.("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, [localArtworkUrl, onArtworkUpload]);

  const formatDims = (w: number, h: number, g: number) => {
    if (g > 0) return `${w}" W × ${h}" H × ${g}" G`;
    return `${w}" W × ${h}" H`;
  };

  return (
    <div className={compact ? "" : "space-y-3"}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-90">3D Preview</h4>
        <span className="text-xs text-gray-60">
          {sealType === "Stand Up Pouch" ? "Stand Up Pouch" : sealType}
        </span>
      </div>

      {/* 3D Canvas */}
      <div
        className={`rounded-lg border border-gray-10 bg-gray-5 overflow-hidden cursor-grab active:cursor-grabbing ${
          compact ? "h-48" : "h-64 sm:h-72"
        }`}
      >
        <Suspense fallback={<LoadingFallback />}>
          <Canvas
            camera={{ position: [0.15, 0.15, 0.4], fov: 35 }}
            dpr={[1, 2]}
            gl={{ antialias: true, alpha: true }}
            style={{ background: "transparent" }}
          >
            <Scene
              modelPath={modelPath}
              materialConfig={materialConfig}
              artworkUrl={localArtworkUrl}
            />
          </Canvas>
        </Suspense>
      </div>

      {/* Artwork upload */}
      <div className="flex items-center gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.pdf,.ai,.eps"
          onChange={handleFileChange}
          className="hidden"
          id="artwork-upload"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex-1 rounded-lg border border-dashed border-gray-30 px-3 py-2 text-xs text-gray-60 hover:border-calyx-blue hover:text-calyx-blue transition-colors"
        >
          {localArtworkUrl ? "Replace artwork" : "Upload artwork to preview"}
        </button>
        {localArtworkUrl && (
          <button
            onClick={handleRemoveArtwork}
            className="rounded-lg border border-gray-10 px-2 py-2 text-xs text-gray-60 hover:text-red-600 hover:border-red-200 transition-colors"
            title="Remove artwork"
          >
            ✕
          </button>
        )}
      </div>

      {/* Dimension label */}
      <p className="text-center text-xs font-medium text-gray-60">
        {formatDims(width, height, gusset)}
        <span className="mx-1.5 text-gray-30">·</span>
        {substrate}
      </p>

      {/* Interaction hint */}
      <p className="text-center text-[10px] text-gray-30">
        Drag to rotate · Scroll to zoom
      </p>
    </div>
  );
}
