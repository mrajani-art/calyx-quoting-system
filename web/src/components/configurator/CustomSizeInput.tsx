"use client";

import { useState, useEffect } from "react";

interface Props {
  width: number;
  height: number;
  gusset: number;
  onChange: (field: "width" | "height" | "gusset", value: number) => void;
}

const fields: {
  key: "width" | "height" | "gusset";
  label: string;
  min: number;
  max: number;
}[] = [
  { key: "width", label: "Width (in)", min: 0.5, max: 20 },
  { key: "height", label: "Height (in)", min: 0.5, max: 20 },
  { key: "gusset", label: "Gusset (in)", min: 0, max: 10 },
];

function DimensionInput({
  field,
  value,
  onChange,
}: {
  field: (typeof fields)[number];
  value: number;
  onChange: (field: "width" | "height" | "gusset", value: number) => void;
}) {
  const [display, setDisplay] = useState(String(value));

  // Sync display when the external value changes (e.g. preset selection)
  useEffect(() => {
    setDisplay(String(value));
  }, [value]);

  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={`custom-${field.key}`}
        className="text-sm font-medium text-gray-90"
      >
        {field.label}
      </label>
      <input
        id={`custom-${field.key}`}
        type="number"
        min={field.min}
        max={field.max}
        step={0.5}
        value={display}
        onChange={(e) => {
          setDisplay(e.target.value);
          const raw = parseFloat(e.target.value);
          if (!Number.isNaN(raw) && raw >= field.min && raw <= field.max) {
            onChange(field.key, raw);
          }
        }}
        onBlur={() => {
          const raw = parseFloat(display);
          if (Number.isNaN(raw) || raw < field.min) {
            const clamped = field.min;
            setDisplay(String(clamped));
            onChange(field.key, clamped);
          } else if (raw > field.max) {
            setDisplay(String(field.max));
            onChange(field.key, field.max);
          } else {
            setDisplay(String(raw));
          }
        }}
        className="rounded-lg border border-gray-10 px-3 py-2 text-sm text-gray-90 transition-shadow focus:border-calyx-blue focus:outline-none focus:ring-2 focus:ring-calyx-blue/30"
      />
    </div>
  );
}

export default function CustomSizeInput({
  width,
  height,
  gusset,
  onChange,
}: Props) {
  const values: Record<"width" | "height" | "gusset", number> = {
    width,
    height,
    gusset,
  };

  return (
    <div className="grid grid-cols-3 gap-4">
      {fields.map((field) => (
        <DimensionInput
          key={field.key}
          field={field}
          value={values[field.key]}
          onChange={onChange}
        />
      ))}
    </div>
  );
}
