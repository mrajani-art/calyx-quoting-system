"use client";

import clsx from "clsx";
import {
  SUBSTRATES,
  FINISHES,
  SEAL_TYPES,
  FILL_STYLES,
  ZIPPERS,
  TEAR_NOTCHES,
  HOLE_PUNCHES,
  CORNERS,
  EMBELLISHMENTS,
} from "@/lib/constants/bag-options";

interface Props {
  substrate: string;
  finish: string;
  sealType: string;
  fillStyle: string;
  zipper: string;
  tearNotch: string;
  holePunch: string;
  corners: string;
  embellishment: string;
  onChange: (field: string, value: string) => void;
}

interface SelectFieldProps {
  id: string;
  label: string;
  value: string;
  options: ReadonlyArray<{ label: string; value: string }>;
  onChange: (value: string) => void;
  disabled?: boolean;
  disabledReason?: string;
}

function SelectField({
  id,
  label,
  value,
  options,
  onChange,
  disabled = false,
  disabledReason,
}: SelectFieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={id}
        className="text-sm font-medium text-gray-90"
      >
        {label}
      </label>
      <select
        id={id}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className={clsx(
          "rounded-lg border border-gray-10 bg-white px-3 py-2 text-sm transition-shadow",
          "focus:border-calyx-blue focus:outline-none focus:ring-2 focus:ring-calyx-blue/30",
          disabled
            ? "cursor-not-allowed bg-gray-5 text-gray-30"
            : "text-gray-90"
        )}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {disabled && disabledReason && (
        <span className="text-xs text-gray-30">{disabledReason}</span>
      )}
    </div>
  );
}

export default function BagOptionsForm({
  substrate,
  finish,
  sealType,
  fillStyle,
  zipper,
  tearNotch,
  holePunch,
  corners,
  embellishment,
  onChange,
}: Props) {
  const isStandUpPouch = sealType === "Stand Up Pouch";

  return (
    <div className="grid grid-cols-2 gap-x-4 gap-y-5">
      {/* Row 1: Seal Type, Fill Style */}
      <SelectField
        id="seal-type"
        label="Seal Type"
        value={sealType}
        options={SEAL_TYPES}
        onChange={(v) => onChange("sealType", v)}
      />
      <SelectField
        id="fill-style"
        label="Fill Style"
        value={isStandUpPouch ? "Top" : fillStyle}
        options={FILL_STYLES}
        onChange={(v) => onChange("fillStyle", v)}
        disabled={isStandUpPouch}
        disabledReason="Stand Up Pouch requires top fill"
      />

      {/* Row 2: Substrate, Finish */}
      <SelectField
        id="substrate"
        label="Substrate"
        value={substrate}
        options={SUBSTRATES}
        onChange={(v) => onChange("substrate", v)}
      />
      <SelectField
        id="finish"
        label="Finish"
        value={finish}
        options={FINISHES}
        onChange={(v) => onChange("finish", v)}
      />

      {/* Row 3: Zipper, Tear Notch */}
      <SelectField
        id="zipper"
        label="Zipper"
        value={zipper}
        options={ZIPPERS}
        onChange={(v) => onChange("zipper", v)}
      />
      <SelectField
        id="tear-notch"
        label="Tear Notch"
        value={tearNotch}
        options={TEAR_NOTCHES}
        onChange={(v) => onChange("tearNotch", v)}
      />

      {/* Row 4: Hole Punch, Corners */}
      <SelectField
        id="hole-punch"
        label="Hole Punch"
        value={holePunch}
        options={HOLE_PUNCHES}
        onChange={(v) => onChange("holePunch", v)}
      />
      <SelectField
        id="corners"
        label="Corners"
        value={corners}
        options={CORNERS}
        onChange={(v) => onChange("corners", v)}
      />

      {/* Row 5: Embellishment (single column) */}
      <SelectField
        id="embellishment"
        label="Embellishment"
        value={embellishment}
        options={EMBELLISHMENTS}
        onChange={(v) => onChange("embellishment", v)}
      />
    </div>
  );
}
