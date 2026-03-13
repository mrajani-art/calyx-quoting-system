"use client";

import { useRef, useState, useEffect } from "react";
import clsx from "clsx";

interface Props {
  tiers: number[];
  activeTier: number;
  onTierClick: (quantity: number) => void;
  onEditTier?: (oldQty: number, newQty: number) => void;
}

const fmt = new Intl.NumberFormat("en-US");

export default function TierSelector({
  tiers,
  activeTier,
  onTierClick,
  onEditTier,
}: Props) {
  const [editingTier, setEditingTier] = useState<number | null>(null);
  const [inputValue, setInputValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus the input when editing starts
  useEffect(() => {
    if (editingTier !== null) {
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, [editingTier]);

  function startEdit(tier: number) {
    if (!onEditTier) return;
    setEditingTier(tier);
    setInputValue(String(tier));
  }

  function confirmEdit() {
    if (editingTier === null) return;
    const parsed = Number(inputValue);
    if (!parsed || parsed <= 0 || !Number.isInteger(parsed)) {
      cancelEdit();
      return;
    }
    // If unchanged, just close
    if (parsed === editingTier) {
      cancelEdit();
      return;
    }
    // Don't allow duplicates
    if (tiers.includes(parsed)) {
      cancelEdit();
      return;
    }
    onEditTier?.(editingTier, parsed);
    setEditingTier(null);
    setInputValue("");
  }

  function cancelEdit() {
    setEditingTier(null);
    setInputValue("");
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      {tiers.map((tier) => {
        const isActive = tier === activeTier;
        const isEditing = editingTier === tier;

        if (isEditing) {
          return (
            <div
              key={tier}
              className="inline-flex items-center rounded-full bg-gray-5 border-2 border-calyx-blue px-2 py-1"
            >
              <input
                ref={inputRef}
                type="number"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") confirmEdit();
                  if (e.key === "Escape") cancelEdit();
                }}
                onBlur={confirmEdit}
                className="w-24 rounded-full bg-white px-2 py-1 text-sm text-center font-medium outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
              />
            </div>
          );
        }

        return (
          <button
            key={tier}
            type="button"
            onClick={() => onTierClick(tier)}
            onDoubleClick={() => startEdit(tier)}
            className={clsx(
              "rounded-full px-4 py-2 text-sm font-medium transition-colors",
              isActive
                ? "bg-calyx-blue text-white"
                : "bg-gray-5 text-gray-60 hover:bg-gray-10",
              onEditTier && "cursor-pointer"
            )}
            title={onEditTier ? "Double-click to edit" : undefined}
          >
            {fmt.format(tier)}
          </button>
        );
      })}
    </div>
  );
}
