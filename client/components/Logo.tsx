export function Logo({ size = 34, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <rect width="32" height="32" rx="9" fill="currentColor" />
      <circle cx="16" cy="12.4" r="4.2" fill="var(--lime)" />
      <path d="M13.35 15.9 12 24h8l-1.35-8.1a5.9 5.9 0 0 1-5.3 0Z" fill="var(--lime)" />
    </svg>
  );
}
