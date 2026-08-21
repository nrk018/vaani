"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Mic, Square, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { useVaani } from "@/hooks/useVaani";
import { ConversationRail } from "./ConversationRail";
import { LatencyHud } from "./LatencyHud";
import { MeshGradientSVG } from "./MeshGradientSVG";
import { Waveform } from "./Waveform";

const HINT: Record<string, string> = {
  idle: "Dev borem korum — tap Vaani and speak",
  listening: "Listening…",
  thinking: "Retrieving evidence…",
  speaking: "Speaking from the passages",
};

type Panel = "log" | "instrument" | null;

export function VoiceStage() {
  const v = useVaani();
  const listening = v.state === "listening";
  const [panel, setPanel] = useState<Panel>(null);

  const latest = [...v.turns].reverse().find((t) => t.role === "vaani");
  const caption =
    v.partial ||
    (v.state === "speaking" ? v.spokenLine : "") ||
    (v.state === "idle" ? v.spokenLine || latest?.text || "" : "");

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPanel(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="relative min-h-screen">
      <section className="absolute inset-x-0 top-0 bottom-[14.5rem] flex flex-col items-center justify-center px-4">
        <button
          type="button"
          className="relative z-10 w-[min(340px,70vw)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/60"
          onClick={() => {
            if (!listening) void v.startListening();
            else v.stopListening();
          }}
          aria-label={listening ? "Stop listening" : "Start listening"}
        >
          <MeshGradientSVG state={v.state} energy={v.energy} />
        </button>
        <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.32em] text-gold/80">
          {HINT[v.state]}
        </p>
      </section>

      <EdgeTab
        side="left"
        label="log"
        open={panel === "log"}
        onClick={() => setPanel(panel === "log" ? null : "log")}
      />
      <EdgeTab
        side="right"
        label="instrument"
        open={panel === "instrument"}
        onClick={() => setPanel(panel === "instrument" ? null : "instrument")}
      />

      <AnimatePresence>
        {panel ? (
          <motion.button
            type="button"
            aria-label="Close panel"
            className="fixed inset-0 z-40 bg-black/45"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setPanel(null)}
          />
        ) : null}
      </AnimatePresence>

      <AnimatePresence>
        {panel === "log" ? (
          <motion.aside
            key="log"
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "spring", stiffness: 380, damping: 36 }}
            className="fixed inset-y-0 left-0 z-50 flex w-[min(20rem,88vw)] flex-col border-r border-gold/20 bg-[#0B6839]/95 backdrop-blur-md"
          >
            <DrawerClose onClick={() => setPanel(null)} />
            <ConversationRail turns={v.turns} partial={v.partial} />
          </motion.aside>
        ) : null}
      </AnimatePresence>

      <AnimatePresence>
        {panel === "instrument" ? (
          <motion.aside
            key="instrument"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 380, damping: 36 }}
            className="fixed inset-y-0 right-0 z-50 flex w-[min(20rem,88vw)] flex-col border-l border-gold/20 bg-[#0B6839]/95 backdrop-blur-md"
          >
            <DrawerClose onClick={() => setPanel(null)} />
            <LatencyHud
              result={v.lastResult}
              citations={v.lastResult?.citations ?? []}
            />
          </motion.aside>
        ) : null}
      </AnimatePresence>

      <div className="fixed inset-x-0 bottom-0 z-30">
        <div className="mx-auto flex w-full max-w-2xl flex-col items-center px-4 pb-2 pt-2">
          <div className="mb-2 flex min-h-[4.75rem] w-full items-end justify-center">
            {caption ? (
              <p className="line-clamp-3 max-w-xl text-center font-serif text-xl leading-snug text-white/90 md:text-2xl">
                {caption}
                {v.state === "speaking" ? (
                  <span
                    aria-hidden
                    className="ml-0.5 inline-block h-[0.85em] w-[2px] translate-y-[0.08em] bg-gold align-baseline"
                  />
                ) : null}
              </p>
            ) : (
              <span className="block h-[4.75rem]" />
            )}
          </div>

          <form
            className="flex w-full gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              void v.runQuery(v.draft);
            }}
          >
            <input
              value={v.draft}
              onChange={(e) => v.setDraft(e.target.value)}
              placeholder="Try: What is the capital of Goa?"
              className="h-11 flex-1 rounded-none border border-gold/40 bg-[#08532e]/80 px-4 text-sm text-sea outline-none placeholder:text-sea/35 focus:border-gold"
            />
            <Button
              type="submit"
              className="h-11 rounded-none bg-gold px-5 font-serif text-lg uppercase tracking-wide text-ink hover:bg-gold/90"
            >
              Ask
            </Button>
            <Button
              type="button"
              size="icon"
              variant="ghost"
              className="h-11 w-11 rounded-none border border-gold/40 text-gold hover:bg-gold/15"
              onClick={() =>
                listening ? v.stopListening() : v.startListening()
              }
            >
              {listening ? (
                <Square className="size-4" />
              ) : (
                <Mic className="size-4" />
              )}
            </Button>
          </form>

          {v.error ? (
            <p className="mt-2 text-xs text-laterite">{v.error}</p>
          ) : null}
        </div>

        <div className="relative">
          <Waveform
            variant="dock"
            active={listening || v.state === "speaking"}
            energy={v.energy}
          />
          <p className="pointer-events-none absolute inset-x-0 bottom-1 text-center font-mono text-[9px] uppercase tracking-[0.2em] text-white/35 md:text-right md:pr-4">
            {v.health
              ? `${v.health.index.n_chunks} chunks · ${v.health.index.embedder} · ${
                  v.health.elevenlabs ? "scribe live" : "voice optional"
                } · ${v.health.groq ? "groq" : "extractive"}`
              : "API offline — start the FastAPI server"}
          </p>
        </div>
      </div>
    </div>
  );
}

function EdgeTab({
  side,
  label,
  open,
  onClick,
  icon,
}: {
  side: "left" | "right";
  label: string;
  open: boolean;
  onClick: () => void;
  icon?: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-expanded={open}
      className={`fixed top-1/2 z-40 flex -translate-y-1/2 items-center gap-2 border border-gold/25 bg-[#08532e]/85 px-2 py-3 font-mono text-[9px] uppercase tracking-[0.22em] text-sea/80 backdrop-blur-md transition hover:text-gold ${
        side === "left"
          ? "left-0 rounded-r-xl border-l-0"
          : "right-0 rounded-l-xl border-r-0"
      } ${open ? "opacity-0" : "opacity-100"}`}
      style={{ writingMode: "vertical-rl" }}
    >
      {icon}
      {label}
    </button>
  );
}

function DrawerClose({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="absolute right-3 top-4 z-10 rounded-full p-1 text-white/45 hover:text-white"
      aria-label="Close"
    >
      <X className="size-4" />
    </button>
  );
}
