"use client";

import clsx from "clsx";
import { Package, Ruler } from "lucide-react";
import { STANDARD_SIZES } from "@/lib/constants/standard-sizes";

interface Props {
  selectedSize: { w: number; h: number; g: number } | null;
  onSelect: (size: { w: number; h: number; g: number } | "custom") => void;
  isCustom: boolean;
}

function formatDimensions(w: number, h: number, g: number): string {
  if (g > 0) {
    return `${w}" x ${h}" x ${g}"`;
  }
  return `${w}" x ${h}"`;
}

export default function StandardSizeSelector({
  selectedSize,
  onSelect,
  isCustom,
}: Props) {
  const flatSizes = STANDARD_SIZES.filter(s => s.g === 0);
  const standUpSizes = STANDARD_SIZES.filter(s => s.g > 0);

  function renderSizeCard(size: (typeof STANDARD_SIZES)[number]) {
    const isSelected =
      !isCustom &&
      selectedSize?.w === size.w &&
      selectedSize?.h === size.h &&
      selectedSize?.g === size.g;

    return (
      <button
        key={`${size.w}-${size.h}-${size.g}-${size.label}`}
        type="button"
        onClick={() =>
          onSelect({ w: size.w, h: size.h, g: size.g })
        }
        className={clsx(
          "flex flex-col items-start gap-1 rounded-lg border-2 p-3 text-left transition-colors",
          isSelected
            ? "border-calyx-blue bg-cloud-blue"
            : "border-gray-10 hover:border-gray-30"
        )}
      >
        <div className="flex items-center gap-1.5">
          <Package
            className={clsx(
              "h-4 w-4 shrink-0",
              isSelected ? "text-calyx-blue" : "text-gray-60"
            )}
          />
          <span
            className={clsx(
              "text-sm font-semibold",
              isSelected ? "text-calyx-blue" : "text-gray-90"
            )}
          >
            {formatDimensions(size.w, size.h, size.g)}
          </span>
        </div>
        <span className="line-clamp-2 text-xs leading-tight text-gray-60">
          {size.label}
        </span>
      </button>
    );
  }

  function renderCustomCard() {
    return (
      <button
        type="button"
        onClick={() => onSelect("custom")}
        className={clsx(
          "flex flex-col items-start gap-1 rounded-lg border-2 p-3 text-left transition-colors",
          isCustom
            ? "border-calyx-blue bg-cloud-blue"
            : "border-gray-10 hover:border-gray-30"
        )}
      >
        <div className="flex items-center gap-1.5">
          <Ruler
            className={clsx(
              "h-4 w-4 shrink-0",
              isCustom ? "text-calyx-blue" : "text-gray-60"
            )}
          />
          <span
            className={clsx(
              "text-sm font-semibold",
              isCustom ? "text-calyx-blue" : "text-gray-90"
            )}
          >
            Custom Size
          </span>
        </div>
        <span className="text-xs leading-tight text-gray-60">
          Enter your own dimensions
        </span>
      </button>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-40 mb-2">Flat Pouches</h4>
        <div className="grid grid-cols-2 gap-3">
          {flatSizes.map(size => renderSizeCard(size))}
        </div>
      </div>
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-40 mb-2">Stand-Up Pouches</h4>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          {standUpSizes.map(size => renderSizeCard(size))}
        </div>
      </div>
      <div>
        <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-40 mb-2">Custom Size</h4>
        <div className="grid grid-cols-2 gap-3">
          {renderCustomCard()}
        </div>
      </div>
    </div>
  );
}
