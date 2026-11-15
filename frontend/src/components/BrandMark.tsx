export function BrandMark({ className = "" }: { className?: string }) {
  return <svg className={className} viewBox="0 0 40 40" fill="none" aria-hidden="true">
    <ellipse cx="20" cy="20" rx="18" ry="10" transform="rotate(-34 20 20)" stroke="currentColor" strokeWidth="1.6" />
    <circle cx="20" cy="20" r="7" stroke="currentColor" strokeWidth="1.6" />
    <circle cx="33.5" cy="10.8" r="3.1" className="orbit-point" />
  </svg>;
}
