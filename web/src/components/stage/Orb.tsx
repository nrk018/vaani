"use client";

import { useEffect, useRef } from "react";
import type { OrbState } from "@/lib/types";

const PALETTE: Record<OrbState, [string, string, string]> = {
  idle: ["#0d3d45", "#1aa7a1", "#e8c36a"],
  listening: ["#3d1a12", "#e07a4c", "#f0d48a"],
  thinking: ["#1a2a44", "#4e8cff", "#c9a44a"],
  speaking: ["#0a4a3c", "#3ee0c4", "#f3d27a"],
};

export function Orb({
  state,
  energy,
}: {
  state: OrbState;
  energy: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let raf = 0;
    let t = 0;
    const dpr = Math.min(2, window.devicePixelRatio || 1);

    const resize = () => {
      const size = Math.min(420, canvas.parentElement?.clientWidth || 420);
      canvas.width = size * dpr;
      canvas.height = size * dpr;
      canvas.style.width = `${size}px`;
      canvas.style.height = `${size}px`;
    };
    resize();
    const onResize = () => resize();
    window.addEventListener("resize", onResize);

    const loop = () => {
      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2;
      const cy = h / 2;
      t += state === "thinking" ? 0.035 : 0.016;
      ctx.clearRect(0, 0, w, h);

      const [c0, c1, c2] = PALETTE[state];
      const radius = (w / 2) * (0.32 + energy * 0.12);

      const glow = ctx.createRadialGradient(cx, cy, radius * 0.2, cx, cy, radius * 2.2);
      glow.addColorStop(0, hexA(c1, 0.55));
      glow.addColorStop(0.45, hexA(c0, 0.18));
      glow.addColorStop(1, hexA(c0, 0));
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, w, h);

      ctx.save();
      ctx.translate(cx, cy);
      const rings = 3;
      for (let i = 0; i < rings; i++) {
        ctx.rotate(t * (0.2 + i * 0.08) * (i % 2 === 0 ? 1 : -1));
        ctx.beginPath();
        ctx.ellipse(0, 0, radius * (1.15 + i * 0.18 + energy * 0.08), radius * (0.92 + i * 0.05), 0.4, 0, Math.PI * 2);
        ctx.strokeStyle = hexA(i === 1 ? c2 : c1, 0.18 - i * 0.04);
        ctx.lineWidth = 1.2 * dpr;
        ctx.stroke();
      }
      ctx.restore();

      const core = ctx.createRadialGradient(
        cx - radius * 0.25,
        cy - radius * 0.3,
        radius * 0.05,
        cx,
        cy,
        radius,
      );
      core.addColorStop(0, "#f7f1de");
      core.addColorStop(0.18, c2);
      core.addColorStop(0.55, c1);
      core.addColorStop(1, c0);
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fillStyle = core;
      ctx.fill();

      const n = 28;
      for (let i = 0; i < n; i++) {
        const a = (i / n) * Math.PI * 2 + t * 0.6;
        const wobble = Math.sin(t * 2 + i) * energy * radius * 0.12;
        const r = radius * 1.28 + wobble;
        const x = cx + Math.cos(a) * r;
        const y = cy + Math.sin(a) * r * 0.92;
        ctx.beginPath();
        ctx.arc(x, y, (1.4 + energy * 2) * dpr, 0, Math.PI * 2);
        ctx.fillStyle = hexA(c2, 0.35 + energy * 0.35);
        ctx.fill();
      }

      raf = requestAnimationFrame(loop);
    };
    loop();
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, [energy, state]);

  return (
    <canvas
      ref={ref}
      aria-hidden
      className="orb-canvas pointer-events-none select-none"
    />
  );
}

function hexA(hex: string, a: number) {
  const n = hex.replace("#", "");
  const r = parseInt(n.slice(0, 2), 16);
  const g = parseInt(n.slice(2, 4), 16);
  const b = parseInt(n.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}
