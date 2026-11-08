"use client";

import { useEffect, useRef } from "react";

/* Outer-to-inner. The tallest bars sit closest to the core. */
const BAR_HEIGHTS = [
  10, 16, 12, 22, 17, 28, 22, 34, 27, 42, 34, 50, 40, 58, 47, 66, 54, 74, 60,
  82, 68, 90, 74, 98, 80, 106, 86, 114, 92, 120, 96, 126, 100, 130, 104, 124,
  96, 116, 88, 108,
];

function Wave({ side }: { side: "left" | "right" }) {
  return (
    <div className={`sc-l-wave sc-l-wave--${side}`} aria-hidden="true">
      {BAR_HEIGHTS.map((height, index) => {
        const distance = index / (BAR_HEIGHTS.length - 1);
        const opacity = side === "left" ? 0.14 + distance * 0.78 : 0.92 - distance * 0.78;
        return (
          <span
            className="sc-l-wave-bar"
            key={`${side}-${index}`}
            style={
              {
                "--bar-height": `${height}px`,
                "--bar-opacity": opacity.toFixed(2),
                "--bar-delay": `${index * 13}ms`,
              } as React.CSSProperties
            }
          />
        );
      })}
    </div>
  );
}

export function HeroStage() {
  const stageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stageNode = stageRef.current;
    if (!stageNode) return;
    const stage: HTMLDivElement = stageNode;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
    if (reduced.matches || !finePointer.matches) return;

    let frame = 0;

    function handleMove(event: PointerEvent) {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const rect = stage.getBoundingClientRect();
        const x = (event.clientX - rect.left) / rect.width - 0.5;
        const y = (event.clientY - rect.top) / rect.height - 0.5;
        stage.style.setProperty("--sc-l-mx", x.toFixed(3));
        stage.style.setProperty("--sc-l-my", y.toFixed(3));
      });
    }

    function handleLeave() {
      cancelAnimationFrame(frame);
      stage.style.setProperty("--sc-l-mx", "0");
      stage.style.setProperty("--sc-l-my", "0");
    }

    stage.addEventListener("pointermove", handleMove);
    stage.addEventListener("pointerleave", handleLeave);

    return () => {
      cancelAnimationFrame(frame);
      stage.removeEventListener("pointermove", handleMove);
      stage.removeEventListener("pointerleave", handleLeave);
    };
  }, []);

  return (
    <div className="sc-l-hero-stage" ref={stageRef}>
      <Wave side="left" />

      <div className="sc-l-core" aria-hidden="true">
        <div className="sc-l-core-tilt">
          <svg className="sc-l-core-svg" viewBox="0 0 480 480" focusable="false">
            <defs>
              <radialGradient id="sc-core-halo" cx="50%" cy="50%" r="50%">
                <stop offset="0" stopColor="#c7f464" stopOpacity="0.16" />
                <stop offset="0.56" stopColor="#c7f464" stopOpacity="0.045" />
                <stop offset="1" stopColor="#c7f464" stopOpacity="0" />
              </radialGradient>
              <radialGradient id="sc-core-shadow">
                <stop offset="0" stopColor="#000000" stopOpacity="0.48" />
                <stop offset="1" stopColor="#000000" stopOpacity="0" />
              </radialGradient>
              <linearGradient id="sc-core-hole-fill" x1="0" y1="0" x2="0.7" y2="1">
                <stop offset="0" stopColor="#143d44" />
                <stop offset="0.55" stopColor="#0a2a31" />
                <stop offset="1" stopColor="#03151a" />
              </linearGradient>
              <linearGradient id="sc-core-plate" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#ffffff" />
                <stop offset="0.4" stopColor="#f3fafa" />
                <stop offset="1" stopColor="#bfd6d6" />
              </linearGradient>
              <linearGradient id="sc-core-edge" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0" stopColor="#ffffff" stopOpacity="0.9" />
                <stop offset="1" stopColor="#9cb7b7" stopOpacity="0.55" />
              </linearGradient>
            </defs>

            <circle cx="240" cy="240" r="228" fill="url(#sc-core-halo)" />
            <ellipse cx="240" cy="452" rx="180" ry="20" fill="url(#sc-core-shadow)" />

            <g className="sc-l-core-layer sc-l-core-layer--back">
              <rect
                x="22"
                y="22"
                width="360"
                height="360"
                rx="76"
                fill="#c7f464"
                fillOpacity="0.05"
                stroke="#c7f464"
                strokeOpacity="0.34"
              />
              <rect
                x="38"
                y="38"
                width="328"
                height="328"
                rx="68"
                fill="none"
                stroke="#c7f464"
                strokeOpacity="0.11"
                strokeDasharray="1 10"
              />
            </g>

            <g className="sc-l-core-layer sc-l-core-layer--mid">
              <rect
                x="41"
                y="41"
                width="360"
                height="360"
                rx="76"
                fill="#f2fafa"
                fillOpacity="0.045"
                stroke="#f2fafa"
                strokeOpacity="0.22"
              />
            </g>

            <g className="sc-l-core-layer sc-l-core-layer--front">
              <rect x="60" y="70" width="360" height="360" rx="76" fill="#8ea8a9" />
              <rect
                x="60"
                y="60"
                width="360"
                height="360"
                rx="76"
                fill="url(#sc-core-plate)"
                stroke="url(#sc-core-edge)"
                strokeWidth="1.6"
              />
              <rect
                x="62"
                y="62"
                width="356"
                height="356"
                rx="74"
                fill="none"
                stroke="#ffffff"
                strokeOpacity="0.55"
                strokeWidth="1.2"
              />
              <line
                x1="82"
                y1="96"
                x2="398"
                y2="96"
                stroke="#062a33"
                strokeOpacity="0.1"
              />
              <text x="86" y="88" className="sc-l-core-serial">
                S-01
              </text>
              <circle
                cx="240"
                cy="286"
                r="96"
                fill="none"
                stroke="#062a33"
                strokeOpacity="0.12"
                strokeDasharray="1 9"
              />
              <g className="sc-l-core-lock">
                <rect
                  x="176"
                  y="256"
                  width="128"
                  height="104"
                  rx="26"
                  fill="url(#sc-core-hole-fill)"
                />
                <path
                  d="M202 264V232A38 38 0 0 1 278 232V264"
                  fill="none"
                  stroke="url(#sc-core-hole-fill)"
                  strokeWidth="18"
                  strokeLinecap="round"
                />
                <rect
                  x="178"
                  y="258"
                  width="124"
                  height="100"
                  rx="24"
                  fill="none"
                  stroke="#f2fafa"
                  strokeOpacity="0.08"
                />
                <circle cx="240" cy="308" r="4.5" fill="#c7f464" />
                <circle
                  cx="240"
                  cy="308"
                  r="9"
                  fill="none"
                  stroke="#c7f464"
                  strokeOpacity="0.22"
                />
              </g>
              <circle cx="240" cy="106" r="3.4" fill="#c7f464" />
              <circle
                cx="240"
                cy="106"
                r="8"
                fill="none"
                stroke="#c7f464"
                strokeOpacity="0.22"
              />
              <text x="240" y="386" textAnchor="middle" className="sc-l-core-word">
                SECRIA
              </text>
            </g>
          </svg>
        </div>
      </div>

      <Wave side="right" />

      <span className="sc-l-callout sc-l-callout--left">01 / Envelope layers</span>
      <span className="sc-l-callout sc-l-callout--right">02 / Audit trail</span>
      <span className="sc-l-status">
        <i className="sc-l-dot" aria-hidden="true" />
        Sealed / API-only plaintext
      </span>
    </div>
  );
}
