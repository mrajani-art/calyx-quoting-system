import { Shape } from "three";
import type { BagVisualProps } from "../../bag-svg/types";
import { MIN_DEPTH } from "../types";

export interface PouchShapeResult {
  shape: Shape;
  /** Depth to extrude along Z — real gusset inches for SUP, thin slab for flat. */
  extrudeDepth: number;
  /** Y position of the gusset fold line (bottom of the bag body above the curve). */
  gussetFoldY: number;
}

/* ------------------------------------------------------------------ */
/*  Corner helper — draws a small rounded corner via quadratic bezier  */
/* ------------------------------------------------------------------ */

function roundedCorner(
  shape: Shape,
  cx: number,
  cy: number,
  toX: number,
  toY: number,
): void {
  shape.quadraticCurveTo(cx, cy, toX, toY);
}

/* ------------------------------------------------------------------ */
/*  Main builder                                                       */
/* ------------------------------------------------------------------ */

export function buildPouchShape(props: BagVisualProps): PouchShapeResult {
  const { width, height, gusset, gussetType, corners } = props;

  const halfW = width / 2;
  const halfH = height / 2;

  const isStandUp =
    gussetType === "Plow Bottom" || gussetType === "K Seal";

  const hasGusset = isStandUp && gusset > 0;

  const extrudeDepth = hasGusset ? gusset : MIN_DEPTH;

  const rounded = corners === "Rounded";
  const cornerR = rounded
    ? Math.min(0.15, halfW * 0.08, halfH * 0.08)
    : 0;

  const shape = new Shape();

  if (isStandUp && gusset > 0) {
    /* ============================================================
       Stand Up Pouch — clockwise from bottom-left
       ============================================================ */

    const gussetDepthY = Math.min(gusset * 0.5, height * 0.15);
    const gussetFoldY = -halfH + gussetDepthY;

    if (gussetType === "Plow Bottom") {
      /*
       * Plow Bottom: U-shaped curve along the bottom edge.
       * Path: bottom-left → up left side → top-left → top-right →
       *       down right side → bottom-right → curve to bottom-left
       */

      // Start at bottom-left (just above gusset curve start)
      shape.moveTo(-halfW + cornerR, gussetFoldY);

      // --- Left side (up) ---
      if (rounded) {
        shape.lineTo(-halfW, gussetFoldY + cornerR);
      }
      shape.lineTo(-halfW, halfH - cornerR);

      // Top-left corner
      if (rounded) {
        roundedCorner(shape, -halfW, halfH, -halfW + cornerR, halfH);
      }

      // --- Top edge ---
      shape.lineTo(halfW - cornerR, halfH);

      // Top-right corner
      if (rounded) {
        roundedCorner(shape, halfW, halfH, halfW, halfH - cornerR);
      }

      // --- Right side (down) ---
      shape.lineTo(halfW, gussetFoldY + cornerR);
      if (rounded) {
        roundedCorner(shape, halfW, gussetFoldY, halfW - cornerR, gussetFoldY);
      } else {
        shape.lineTo(halfW, gussetFoldY);
      }

      // --- Plow bottom curve: right → center-bottom → left ---
      shape.quadraticCurveTo(halfW * 0.5, -halfH, 0, -halfH);
      shape.quadraticCurveTo(-halfW * 0.5, -halfH, -halfW + cornerR, gussetFoldY);

      return { shape, extrudeDepth, gussetFoldY };
    }

    /* --- K Seal: V-fold along bottom edge --- */

    // Start at bottom-left
    shape.moveTo(-halfW + cornerR, gussetFoldY);

    // Left side (up)
    if (rounded) {
      shape.lineTo(-halfW, gussetFoldY + cornerR);
    }
    shape.lineTo(-halfW, halfH - cornerR);

    // Top-left corner
    if (rounded) {
      roundedCorner(shape, -halfW, halfH, -halfW + cornerR, halfH);
    }

    // Top edge
    shape.lineTo(halfW - cornerR, halfH);

    // Top-right corner
    if (rounded) {
      roundedCorner(shape, halfW, halfH, halfW, halfH - cornerR);
    }

    // Right side (down)
    shape.lineTo(halfW, gussetFoldY + cornerR);
    if (rounded) {
      roundedCorner(shape, halfW, gussetFoldY, halfW - cornerR, gussetFoldY);
    } else {
      shape.lineTo(halfW, gussetFoldY);
    }

    // K-Seal V-fold: right → center bottom → left
    shape.lineTo(0, -halfH);
    shape.lineTo(-halfW + cornerR, gussetFoldY);

    return { shape, extrudeDepth, gussetFoldY };
  }

  /* ============================================================
     Flat Pouch — simple rectangle (with optional rounded corners)
     ============================================================ */

  const gussetFoldY = -halfH; // no fold line

  if (rounded) {
    // Start mid-bottom-left edge (just right of bottom-left corner)
    shape.moveTo(-halfW + cornerR, -halfH);

    // Bottom edge → bottom-right corner
    shape.lineTo(halfW - cornerR, -halfH);
    roundedCorner(shape, halfW, -halfH, halfW, -halfH + cornerR);

    // Right edge → top-right corner
    shape.lineTo(halfW, halfH - cornerR);
    roundedCorner(shape, halfW, halfH, halfW - cornerR, halfH);

    // Top edge → top-left corner
    shape.lineTo(-halfW + cornerR, halfH);
    roundedCorner(shape, -halfW, halfH, -halfW, halfH - cornerR);

    // Left edge → bottom-left corner
    shape.lineTo(-halfW, -halfH + cornerR);
    roundedCorner(shape, -halfW, -halfH, -halfW + cornerR, -halfH);
  } else {
    shape.moveTo(-halfW, -halfH);
    shape.lineTo(halfW, -halfH);
    shape.lineTo(halfW, halfH);
    shape.lineTo(-halfW, halfH);
    shape.lineTo(-halfW, -halfH);
  }

  return { shape, extrudeDepth, gussetFoldY };
}
