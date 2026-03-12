import clsx from "clsx";

interface Props {
  tiers: number[];
  selectedTier: number;
  onSelect: (quantity: number) => void;
}

const numberFmt = new Intl.NumberFormat("en-US");

export function TierButtons({ tiers, selectedTier, onSelect }: Props) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      {tiers.map((qty) => (
        <button
          key={qty}
          type="button"
          onClick={() => onSelect(qty)}
          className={clsx(
            "shrink-0 rounded-full px-4 py-1.5 text-sm font-medium transition-colors",
            qty === selectedTier
              ? "bg-calyx-blue text-white"
              : "border border-gray-10 bg-white text-gray-60 hover:border-calyx-blue",
          )}
        >
          {numberFmt.format(qty)}
        </button>
      ))}
    </div>
  );
}
