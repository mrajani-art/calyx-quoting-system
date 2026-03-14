"use client";

import clsx from "clsx";
import { ChevronDown } from "lucide-react";
import {
  SUBSTRATES,
  FINISHES,
  SEAL_TYPES,
  FILL_STYLES,
  GUSSET_TYPES,
  ZIPPERS,
  TEAR_NOTCHES,
  HOLE_PUNCHES,
  CORNERS,
  OPTION_DESCRIPTIONS,
} from "@/lib/constants/bag-options";

interface Props {
  substrate: string;
  finish: string;
  sealType: string;
  fillStyle: string;
  gussetType: string;
  zipper: string;
  tearNotch: string;
  holePunch: string;
  corners: string;
  gusset: number;
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
  helpText?: string;
}

function SelectField({
  id,
  label,
  value,
  options,
  onChange,
  disabled = false,
  disabledReason,
  helpText,
}: SelectFieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={id}
        className="text-sm font-medium text-gray-90"
      >
        {label}
      </label>
      {helpText && (
        <span className="text-xs text-gray-40">{helpText}</span>
      )}
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

function OptionGroup({ title, description, defaultOpen, children }: { title: string; description?: string; defaultOpen?: boolean; children: React.ReactNode }) {
  return (
    <details open={defaultOpen} className="group rounded-lg border border-gray-10 bg-white">
      <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-sm font-semibold text-gray-90 select-none [&::-webkit-details-marker]:hidden">
        <div>
          <span>{title}</span>
          {description && <p className="mt-0.5 text-xs font-normal text-gray-50">{description}</p>}
        </div>
        <ChevronDown className="h-4 w-4 text-gray-40 transition-transform group-open:rotate-180" />
      </summary>
      <div className="border-t border-gray-10 px-4 py-4">
        <div className="grid grid-cols-2 gap-x-4 gap-y-5">
          {children}
        </div>
      </div>
    </details>
  );
}

export default function BagOptionsForm({
  substrate,
  finish,
  sealType,
  fillStyle,
  gussetType,
  zipper,
  tearNotch,
  holePunch,
  corners,
  gusset,
  onChange,
}: Props) {
  const isStandUpPouch = sealType === "Stand Up Pouch";
  const hasGusset = gusset > 0;

  return (
    <div className="space-y-3">
      {/* Group 1: Bag Structure */}
      <OptionGroup title="Bag Structure" description="Shape and fill configuration" defaultOpen>
        <SelectField
          id="seal-type"
          label="Seal Type"
          value={sealType}
          options={SEAL_TYPES}
          onChange={(v) => onChange("sealType", v)}
          helpText={OPTION_DESCRIPTIONS.sealType}
        />
        {!isStandUpPouch && (
          <SelectField
            id="fill-style"
            label="Fill Style"
            value={fillStyle}
            options={FILL_STYLES}
            onChange={(v) => onChange("fillStyle", v)}
            helpText={OPTION_DESCRIPTIONS.fillStyle}
          />
        )}
        {hasGusset && (
          <SelectField
            id="gusset-type"
            label="Gusset Type"
            value={gussetType}
            options={GUSSET_TYPES}
            onChange={(v) => onChange("gussetType", v)}
            helpText={OPTION_DESCRIPTIONS.gussetType}
          />
        )}
      </OptionGroup>

      {/* Group 2: Material & Finish */}
      <OptionGroup title="Material & Finish" description="Appearance and barrier properties" defaultOpen>
        <SelectField
          id="substrate"
          label="Substrate"
          value={substrate}
          options={SUBSTRATES}
          onChange={(v) => onChange("substrate", v)}
          helpText={OPTION_DESCRIPTIONS.substrate}
        />
        <SelectField
          id="finish"
          label="Finish"
          value={finish}
          options={FINISHES}
          onChange={(v) => onChange("finish", v)}
          helpText={OPTION_DESCRIPTIONS.finish}
        />
      </OptionGroup>

      {/* Group 3: Closures & Features */}
      <OptionGroup title="Closures & Features" description="Zipper, tear notch, and physical features">
        <SelectField
          id="zipper"
          label="Zipper"
          value={zipper}
          options={ZIPPERS}
          onChange={(v) => onChange("zipper", v)}
          helpText={OPTION_DESCRIPTIONS.zipper}
        />
        <SelectField
          id="tear-notch"
          label="Tear Notch"
          value={tearNotch}
          options={TEAR_NOTCHES}
          onChange={(v) => onChange("tearNotch", v)}
          helpText={OPTION_DESCRIPTIONS.tearNotch}
        />
        <SelectField
          id="hole-punch"
          label="Hole Punch"
          value={holePunch}
          options={HOLE_PUNCHES}
          onChange={(v) => onChange("holePunch", v)}
          helpText={OPTION_DESCRIPTIONS.holePunch}
        />
        <SelectField
          id="corners"
          label="Corners"
          value={corners}
          options={CORNERS}
          onChange={(v) => onChange("corners", v)}
          helpText={OPTION_DESCRIPTIONS.corners}
        />
      </OptionGroup>
    </div>
  );
}
