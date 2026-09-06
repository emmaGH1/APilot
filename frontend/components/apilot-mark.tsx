import type { SVGProps } from "react";

/**
 * APilot mark — "controlled flight path".
 *
 * Three ledger/control strokes (left leg, right leg, crossbar) converge into
 * an A whose right leg opens into a forward chevron (check/forward path).
 * Strokes use `currentColor` so the mark inherits the surrounding tile;
 * the forward chevron carries the restrained warm-gold accent.
 */
export function APilotMark({
  size = 20,
  ...props
}: SVGProps<SVGSVGElement> & { size?: number }) {
  return (
    <svg
      role="img"
      aria-label="APilot"
      focusable="false"
      viewBox="0 0 64 64"
      width={size}
      height={size}
      {...props}
    >
      <g fill="none" stroke="currentColor" strokeWidth={9} strokeLinecap="round" strokeLinejoin="round">
        <path d="M17 51 L31 15.5" />
        <path d="M31 15.5 L45.5 42" />
        <path d="M23 39 L42.5 39" />
      </g>
      <path
        d="M45.5 42 L55 35.5 M45.5 42 L55 49"
        fill="none"
        stroke="#B9852B"
        strokeWidth={8}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
