"use client";

import { Mic, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useVaani } from "@/hooks/useVaani";
import { Constellation } from "./Constellation";
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

export function VoiceStage() {
  const v = useVaani();
  const listening = v.state === "listening";

  return (
    <div className="grid min-h-screen grid-cols-1 md:grid-cols-[280px_1fr_260px]">
      <ConversationRail turns={v.turns} partial={v.partial} />

      <section className="relative flex min-h-[70vh] flex-col items-center justify-center px-4 pb-16 pt-20">
        <div className="relative flex h-[min(420px,58vw)] w-[min(340px,70vw)] items-center justify-center">
          <button
            type="button"
            className="relative z-10 w-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold/60"
            onClick={() => {
              if (!listening) void v.startListening();
              else v.stopListening();
            }}
            aria-label={listening ? "Stop listening" : "Start listening"}
          >
            <MeshGradientSVG state={v.state} energy={v.energy} />
          </button>
        </div>
        <Constellation citations={v.lastResult?.citations ?? []} />

        <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.32em] text-gold/80">
          {HINT[v.state]}
        </p>
        <div className="mt-4 w-full max-w-md">
          <Waveform active={listening || v.state === "speaking"} energy={v.energy} />
        </div>
        {v.turns.at(-1)?.role === "vaani" && v.turns.at(-1)?.text ? (
          <p className="mt-6 max-w-xl text-center font-serif text-2xl leading-snug text-white/90 md:text-3xl">
            {v.turns.at(-1)?.text}
          </p>
        ) : null}

        <form
          className="mt-8 flex w-full max-w-lg gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            void v.runQuery(v.draft);
          }}
        >
          <input
            value={v.draft}
            onChange={(e) => v.setDraft(e.target.value)}
            placeholder="Try: What is the capital of Goa?"
            className="h-11 flex-1 rounded-full border border-gold/20 bg-white/5 px-4 text-sm text-white outline-none placeholder:text-white/30 focus:border-sea/60"
          />
          <Button
            type="submit"
            className="h-11 rounded-full bg-gold px-5 text-[#1A1A2E] hover:bg-gold/90"
          >
            Ask
          </Button>
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="h-11 w-11 rounded-full border border-gold/25 text-white hover:bg-gold/10"
            onClick={() => (listening ? v.stopListening() : v.startListening())}
          >
            {listening ? <Square className="size-4" /> : <Mic className="size-4" />}
          </Button>
        </form>
        {v.error ? (
          <p className="mt-3 text-xs text-laterite">{v.error}</p>
        ) : null}
        {v.health ? (
          <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.2em] text-white/30">
            {v.health.index.n_chunks} chunks · {v.health.index.embedder} ·{" "}
            {v.health.elevenlabs ? "scribe live" : "voice optional"} ·{" "}
            {v.health.groq ? "groq" : "extractive"}
          </p>
        ) : (
          <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.2em] text-white/30">
            API offline — start the FastAPI server
          </p>
        )}
        <div className="mt-5 flex max-w-lg flex-wrap justify-center gap-2">
          {[
            "What is the capital of Goa?",
            "What is Vaani?",
            "What is Hacker House Goa?",
            "गोवा की राजधानी क्या है?",
          ].map((q) => (
            <button
              key={q}
              type="button"
              className="rounded-full border border-gold/20 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-white/55 hover:border-sea/50 hover:text-sea"
              onClick={() => void v.runQuery(q)}
            >
              {q}
            </button>
          ))}
        </div>
      </section>

      <LatencyHud result={v.lastResult} />
    </div>
  );
}
