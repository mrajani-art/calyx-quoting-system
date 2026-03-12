"use client";

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
        <div key={field.key} className="flex flex-col gap-1.5">
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
            value={values[field.key]}
            onChange={(e) => {
              const raw = parseFloat(e.target.value);
              if (!Number.isNaN(raw)) {
                const clamped = Math.min(
                  field.max,
                  Math.max(field.min, raw)
                );
                onChange(field.key, clamped);
              }
            }}
            className="rounded-lg border border-gray-10 px-3 py-2 text-sm text-gray-90 transition-shadow focus:border-calyx-blue focus:outline-none focus:ring-2 focus:ring-calyx-blue/30"
          />
        </div>
      ))}
    </div>
  );
}
