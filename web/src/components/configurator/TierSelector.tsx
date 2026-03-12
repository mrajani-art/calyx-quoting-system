"use client";

import clsx from "clsx";

interface Props {
  tiers: number[];
  activeTier: number;
  onTierClick: (quantity: number) => void;
}

const fmt = new Intl.NumberFormat("en-US");

export default function TierSelector({
  tiers,
  activeTier,
  onTierClick,
}: Props) {
  return (
    <div className="flex flex-wrap gap-2">
      {tiers.map((tier) => {
        const isActive = tier === activeTier;
        return (
          <button
            key={tier}
            type="button"
            onClick={() => onTierClick(tier)}
            className={clsx(
              "rounded-full px-4 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-calyx-blue text-white"
                : "bg-gray-5 text-gray-60 hover:bg-gray-10"
            )}
          >
            {fmt.format(tier)}
          </button>
        );
      })}
    </div>
  );
}
