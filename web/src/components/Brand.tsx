const LAKE = "M11.2 9.4c2.3-1.8 5.6-2.1 7.9-.6 1.1.7 1.8 1.9 3 2.3 1.6.5 2.8 1.9 2.9 3.6.2 2.5-1.5 4.2-3.2 5.7-1.8 1.6-3.3 3.8-5.9 3.9-2.8.1-5.2-1.6-6.4-4.1-.8-1.6-.9-3.4-.6-5.1.3-2.1.8-4.3 2.3-5.7z";

/** The GeoGuard mark: a water body inside its dashed full-tank-level boundary. */
export function BrandMark({ className = "brand-mark" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <path d={LAKE} fill="currentColor" />
      <path
        d={LAKE}
        transform="translate(16 16) scale(1.42) translate(-16 -16)"
        stroke="currentColor"
        strokeWidth="1.15"
        strokeDasharray="1.6 1.9"
        strokeLinecap="round"
        opacity="0.8"
      />
    </svg>
  );
}
