"use client";

import { MeshGradient } from "@paper-design/shaders-react";
import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import type { OrbState } from "@/lib/types";

const COLORS = [
  "#FEE101",
  "#FFFBE8",
  "#0B6839",
  "#127A44",
  "#063D22",
];

const SILHOUETTE =
  "M230.809 115.385V249.411C230.809 269.923 214.985 287.282 194.495 288.411C184.544 288.949 175.364 285.718 168.26 280C159.746 273.154 147.769 273.461 139.178 280.23C132.638 285.384 124.381 288.462 115.379 288.462C106.377 288.462 98.1451 285.384 91.6055 280.23C82.912 273.385 70.9353 273.385 62.2415 280.23C55.7532 285.334 47.598 288.411 38.7246 288.462C17.4132 288.615 0 270.667 0 249.359V115.385C0 51.6667 51.6756 0 115.404 0C179.134 0 230.809 51.6667 230.809 115.385Z";

// CSS mask scales with the box. SVG clipPath on foreignObject is ignored in Safari.
const MASK = `url("data:image/svg+xml,${encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 231 289"><path fill="white" d="${SILHOUETTE}"/></svg>`,
)}")`;

const MOTION: Record<
  OrbState,
  { y: number[]; scaleY: number[]; duration: number; speed: number }
> = {
  idle: { y: [0, -8, 0], scaleY: [1, 1.08, 1], duration: 2.8, speed: 1 },
  listening: { y: [0, -14, 0], scaleY: [1, 1.12, 1], duration: 1.35, speed: 1.7 },
  thinking: { y: [0, -5, 0], scaleY: [1, 1.04, 1], duration: 3.2, speed: 0.55 },
  speaking: { y: [0, -12, 0], scaleY: [1, 1.1, 1], duration: 1.7, speed: 1.45 },
};

export function MeshGradientSVG({
  state = "idle",
  energy = 0.12,
}: {
  state?: OrbState;
  energy?: number;
}) {
  const boxRef = useRef<HTMLDivElement>(null);
  const [eyeOffset, setEyeOffset] = useState({ x: 0, y: 0 });
  const anim = MOTION[state];
  const lift = energy * 10;

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const rect = boxRef.current?.getBoundingClientRect();
      if (!rect) return;
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const maxOffset = 8;
      setEyeOffset({
        x: Math.max(-maxOffset, Math.min(maxOffset, (e.clientX - centerX) * 0.08)),
        y: Math.max(-maxOffset, Math.min(maxOffset, (e.clientY - centerY) * 0.08)),
      });
    };
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  return (
    <motion.div
      className="relative mx-auto w-full max-w-sm p-4"
      animate={{
        y: anim.y.map((v, i) => (i === 1 ? v - lift : v)),
        scaleY: anim.scaleY,
      }}
      transition={{
        duration: anim.duration,
        repeat: Number.POSITIVE_INFINITY,
        ease: "easeInOut",
      }}
      style={{ transformOrigin: "top center" }}
    >
      <div
        ref={boxRef}
        className="relative w-full"
        style={{ aspectRatio: "231 / 289" }}
      >
        <div
          className="absolute inset-0 overflow-hidden"
          style={{
            WebkitMaskImage: MASK,
            maskImage: MASK,
            WebkitMaskSize: "100% 100%",
            maskSize: "100% 100%",
            WebkitMaskRepeat: "no-repeat",
            maskRepeat: "no-repeat",
            WebkitMaskPosition: "center",
            maskPosition: "center",
          }}
        >
          <MeshGradient
            colors={COLORS}
            speed={anim.speed}
            width="100%"
            height="100%"
            className="h-full w-full"
          />
        </div>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 231 289"
          className="pointer-events-none absolute inset-0 h-full w-full select-none"
          aria-hidden
        >
          <motion.ellipse
            cx={80}
            cy={120}
            rx={20}
            ry={30}
            fill="#063D22"
            initial={false}
            animate={{
              cx: 80 + eyeOffset.x,
              cy: 120 + eyeOffset.y,
              ry: [30, 30, 3, 30],
            }}
            transition={{
              cx: { type: "spring", stiffness: 150, damping: 15 },
              cy: { type: "spring", stiffness: 150, damping: 15 },
              ry: {
                duration: 3,
                repeat: Number.POSITIVE_INFINITY,
                times: [0, 0.9, 0.95, 1],
                ease: "easeInOut",
              },
            }}
          />
          <motion.ellipse
            cx={150}
            cy={120}
            rx={20}
            ry={30}
            fill="#063D22"
            initial={false}
            animate={{
              cx: 150 + eyeOffset.x,
              cy: 120 + eyeOffset.y,
              ry: [30, 30, 3, 30],
            }}
            transition={{
              cx: { type: "spring", stiffness: 150, damping: 15 },
              cy: { type: "spring", stiffness: 150, damping: 15 },
              ry: {
                duration: 3,
                repeat: Number.POSITIVE_INFINITY,
                times: [0, 0.9, 0.95, 1],
                ease: "easeInOut",
              },
            }}
          />
        </svg>
      </div>
    </motion.div>
  );
}
