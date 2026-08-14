"use client";

export function Waveform({
  active,
  energy,
}: {
  active: boolean;
  energy: number;
}) {
  const bars = 32;
  return (
    <div className="flex h-10 items-end justify-center gap-[3px]" aria-hidden>
      {Array.from({ length: bars }).map((_, i) => {
        const wave = Math.sin(i * 0.45) * 0.5 + 0.5;
        const h = active ? 8 + (wave * 28 + energy * 22) * (0.4 + (i % 5) / 8) : 4 + wave * 6;
        return (
          <span
            key={i}
            className="w-[3px] rounded-full bg-gradient-to-t from-teal-700/40 to-gold/90 transition-[height] duration-150"
            style={{ height: `${Math.min(40, h)}px`, opacity: active ? 1 : 0.35 }}
          />
        );
      })}
    </div>
  );
}
