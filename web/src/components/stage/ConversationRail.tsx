"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import type { Turn } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ConversationRail({
  turns,
  partial,
}: {
  turns: Turn[];
  partial: string;
}) {
  return (
    <aside className="flex h-full flex-col border-white/8 bg-black/20 backdrop-blur-md md:border-r">
      <header className="px-5 pb-3 pt-6">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-sea/70">
          conversation
        </p>
        <h2 className="font-serif text-2xl text-white/90">Stage log</h2>
      </header>
      <ScrollArea className="flex-1 px-5 pb-6">
        <div className="space-y-4">
          {turns.length === 0 && !partial ? (
            <p className="text-sm leading-relaxed text-white/45">
              Dev borem korum. Speak in English or Hindi. Vaani answers only
              from evidence.
            </p>
          ) : null}
          {turns.map((t) => (
            <div key={t.id} className="space-y-1">
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-gold/70">
                {t.role === "user" ? "you" : "vaani"}
                {t.result ? ` · ${t.result.verdict}` : ""}
              </p>
              <p
                className={cn(
                  "text-sm leading-relaxed",
                  t.role === "user" ? "text-white/80" : "text-sea-fg",
                  t.partial && "opacity-70",
                )}
              >
                {t.text || "…"}
              </p>
            </div>
          ))}
          {partial ? (
            <div className="space-y-1">
              <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-laterite">
                listening
              </p>
              <p className="text-sm text-white/60">{partial}</p>
            </div>
          ) : null}
        </div>
      </ScrollArea>
    </aside>
  );
}
