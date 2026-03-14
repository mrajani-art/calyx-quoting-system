export default function ResultsSkeleton() {
  return (
    <div className="space-y-8 animate-pulse">
      {/* Header skeleton */}
      <div>
        <div className="h-8 w-64 bg-gray-10 rounded" />
        <div className="mt-2 h-4 w-96 bg-gray-5 rounded" />
      </div>

      {/* Spec summary skeleton */}
      <div className="rounded-xl border border-gray-10 bg-white p-5 flex gap-6">
        <div className="w-40 h-48 bg-gray-5 rounded-lg shrink-0" />
        <div className="grid grid-cols-2 gap-x-6 gap-y-4 flex-1">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i}>
              <div className="h-3 w-16 bg-gray-10 rounded mb-1.5" />
              <div className="h-4 w-24 bg-gray-5 rounded" />
            </div>
          ))}
        </div>
      </div>

      {/* Tier selector skeleton */}
      <div>
        <div className="h-5 w-32 bg-gray-10 rounded mb-3" />
        <div className="flex gap-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-9 w-20 bg-gray-5 rounded-full" />
          ))}
        </div>
      </div>

      {/* Pricing grid skeleton */}
      <div className="rounded-xl border border-gray-10 overflow-hidden">
        <div className="bg-gray-5 px-4 py-3 flex gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex-1">
              <div className="h-4 w-20 bg-gray-10 rounded mb-1" />
              <div className="h-3 w-32 bg-gray-10/50 rounded" />
            </div>
          ))}
        </div>
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="border-t border-gray-10 px-4 py-3 flex gap-4">
            {Array.from({ length: 4 }).map((_, j) => (
              <div key={j} className="flex-1">
                <div className="h-5 w-16 bg-gray-5 rounded mb-1" />
                <div className="h-3 w-12 bg-gray-5/50 rounded" />
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
