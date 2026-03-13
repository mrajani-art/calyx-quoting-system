"use client";

import { useRef, useState } from "react";
import clsx from "clsx";
import { Check, Plus, X } from "lucide-react";

interface Props {
  tiers: number[];
  activeTier: number;
  onTierClick: (quantity: number) => void;
  onAddTier?: (qty: number) => void;
  onRemoveTier?: (qty: number) => void;
  minTiers?: number;
}

const fmt = new Intl.NumberFormat("en-US");

export default function TierSelector({
  tiers,
  activeTier,
  onTierClick,
  onAddTier,
  onRemoveTier,
  minTiers = 1,
}: Props) {
  const [adding, setAdding] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const canRemove = tiers.length > minTiers;

  function openInput() {
    setInputValue("");
    setAdding(true);
    // auto-focus after React renders the input
    setTimeout(() => inputRef.current?.focus(), 0);
  }

  function closeInput() {
    setAdding(false);
    setInputValue("");
  }

  function confirmAdd() {
    const parsed = Number(inputValue);
    if (!parsed || parsed <= 0 || !Number.isInteger(parsed)) return;
    if (tiers.includes(parsed)) return;
    if (tiers.length >= 10) return;
    onAddTier?.(parsed);
    closeInput();
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {tiers.map((tier) => {
        const isActive = tier === activeTier;
        return (
          <button
            key={tier}
            type="button"
            onClick={() => onTierClick(tier)}
            className={clsx(
              "group relative inline-flex items-center gap-1 rounded-full px-4 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-calyx-blue text-white"
                : "bg-gray-5 text-gray-60 hover:bg-gray-10"
            )}
          >
            {fmt.format(tier)}

            {onRemoveTier && canRemove && (
              <span
                role="button"
                tabIndex={-1}
                onClick={(e) => {
                  e.stopPropagation();
                  onRemoveTier(tier);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.stopPropagation();
                    onRemoveTier(tier);
                  }
                }}
                className={clsx(
                  "ml-1 inline-flex items-center justify-center rounded-full transition-opacity",
                  isActive
                    ? "opacity-50 hover:opacity-100"
                    : "opacity-30 group-hover:opacity-60 hover:!opacity-100"
                )}
              >
                <X size={12} />
              </span>
            )}
          </button>
        );
      })}

      {onAddTier && !adding && (
        <button
          type="button"
          onClick={openInput}
          className="inline-flex items-center justify-center rounded-full border-2 border-dashed border-gray-20 px-3 py-2 text-sm font-medium text-gray-40 transition-colors hover:border-gray-40 hover:text-gray-60"
        >
          <Plus size={14} />
        </button>
      )}

      {onAddTier && adding && (
        <div className="inline-flex items-center gap-1 rounded-full bg-gray-5 px-2 py-1">
          <input
            ref={inputRef}
            type="number"
            placeholder="Qty"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") confirmAdd();
              if (e.key === "Escape") closeInput();
            }}
            className="w-20 rounded-full bg-white px-2 py-1 text-sm outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
          />
          <button
            type="button"
            onClick={confirmAdd}
            className="inline-flex items-center justify-center rounded-full p-1 text-green-600 transition-colors hover:bg-green-50"
          >
            <Check size={14} />
          </button>
          <button
            type="button"
            onClick={closeInput}
            className="inline-flex items-center justify-center rounded-full p-1 text-gray-40 transition-colors hover:bg-gray-10"
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
