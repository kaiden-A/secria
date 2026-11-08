import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Svg({ size = 18, children, ...props }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  );
}

export function ArrowRight(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </Svg>
  );
}

export function Check(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m5 12.5 4.2 4.2L19 7" />
    </Svg>
  );
}

export function Lock(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="5" y="10" width="14" height="10" rx="2.5" />
      <path d="M8.5 10V7.8a3.5 3.5 0 0 1 7 0V10" />
    </Svg>
  );
}

export function Shield(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 3.5 19 6v5.4c0 4.2-2.9 7.6-7 9.1-4.1-1.5-7-4.9-7-9.1V6l7-2.5Z" />
      <path d="m9 12 2 2 4-4.2" />
    </Svg>
  );
}

export function History(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3L4.5 9" />
      <path d="M4.5 4.5V9H9" />
      <path d="M12 8v4.2l2.7 1.6" />
    </Svg>
  );
}

export function Terminal(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="3.5" y="5" width="17" height="14" rx="2.5" />
      <path d="m7.5 10 2.5 2-2.5 2M12.5 14h4" />
    </Svg>
  );
}

export function Layers(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m12 3.5 8 4.3-8 4.3-8-4.3 8-4.3Z" />
      <path d="m4 12.3 8 4.3 8-4.3M4 16.5l8 4.3 8-4.3" />
    </Svg>
  );
}

export function KeyRound(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="8.2" cy="8.2" r="3.7" />
      <path d="m11 11 8 8M16 16l2-2M18.5 18.5l2-2" />
    </Svg>
  );
}

export function EyeOff(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 3l18 18" />
      <path d="M10.6 6.4A9.7 9.7 0 0 1 12 6.3c5 0 8.5 5.7 8.5 5.7a16 16 0 0 1-3.1 3.7M6.2 6.2A16.3 16.3 0 0 0 3.5 12s3.5 5.7 8.5 5.7a9.3 9.3 0 0 0 3.8-.8" />
    </Svg>
  );
}

export function Copy(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="8" y="8" width="11" height="11" rx="2" />
      <path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" />
    </Svg>
  );
}

export function Globe(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M3.5 12h17M12 3.5c2.2 2.4 3.4 5.3 3.4 8.5S14.2 18.1 12 20.5c-2.2-2.4-3.4-5.3-3.4-8.5S9.8 5.9 12 3.5Z" />
    </Svg>
  );
}

export function Eye(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M2.8 12S6.2 5.8 12 5.8 21.2 12 21.2 12 17.8 18.2 12 18.2 2.8 12 2.8 12Z" />
      <circle cx="12" cy="12" r="2.9" />
    </Svg>
  );
}

export function ArrowDown(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 5v14M6 13l6 6 6-6" />
    </Svg>
  );
}
