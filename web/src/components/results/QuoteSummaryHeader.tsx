"use client";

import BagPreview from "@/components/configurator/BagPreview";
import type { BagVisualProps } from "@/components/configurator/bag-svg/types";

interface Props {
  visualProps: BagVisualProps;
}

function formatSize(width: number, height: number, gusset: number): string {
  if (gusset > 0) return `${width}" \u00d7 ${height}" \u00d7 ${gusset}"`;
  return `${width}" \u00d7 ${height}"`;
}

const specs: { label: string; key: string }[] = [
  { label: "Size", key: "size" },
  { label: "Seal Type", key: "sealType" },
  { label: "Substrate", key: "substrate" },
  { label: "Finish", key: "finish" },
  { label: "Zipper", key: "zipper" },
  { label: "Gusset Type", key: "gussetType" },
  { label: "Tear Notch", key: "tearNotch" },
  { label: "Hole Punch", key: "holePunch" },
  { label: "Corners", key: "corners" },
  { label: "Embellishment", key: "embellishment" },
];

function getSpecValue(key: string, visualProps: BagVisualProps): string {
  if (key === "size") {
    return formatSize(visualProps.width, visualProps.height, visualProps.gusset);
  }
  return visualProps[key as keyof BagVisualProps] as string;
}

export default function QuoteSummaryHeader({ visualProps }: Props) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-gray-90 mb-3">
        Your Bag Specifications
      </h3>

      <div className="rounded-xl border border-gray-10 bg-white p-5 flex flex-col sm:flex-row gap-6 items-start">
        {/* Left: compact bag preview */}
        <div className="shrink-0">
          <BagPreview compact {...visualProps} />
        </div>

        {/* Right: spec grid */}
        <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          {specs.map(({ label, key }) => (
            <div key={key}>
              <dt className="text-gray-40 text-xs uppercase tracking-wide">
                {label}
              </dt>
              <dd className="text-gray-90 font-medium">
                {getSpecValue(key, visualProps)}
              </dd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
