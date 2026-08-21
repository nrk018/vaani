"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  askStream,
  fetchHealth,
  fetchScribeToken,
  speak,
} from "@/lib/api";
import type { AskResult, Health, OrbState, Turn } from "@/lib/types";

export function useVaani() {
  const [state, setState] = useState<OrbState>("idle");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [partial, setPartial] = useState("");
  const [energy, setEnergy] = useState(0.12);
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<AskResult | null>(null);
  const [draft, setDraft] = useState("");
  const [spokenLine, setSpokenLine] = useState("");
  const rafRef = useRef<number>(0);
  const scribeRef = useRef<{ close: () => void; commit: () => void } | null>(
    null,
  );
  const audioCtxRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<AudioBufferSourceNode | null>(null);
  const recRef = useRef<{ stop: () => void } | null>(null);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  const unlockAudio = useCallback(async () => {
    const AC =
      window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext })
        .webkitAudioContext;
    if (!AC) return null;
    if (!audioCtxRef.current) audioCtxRef.current = new AC();
    if (audioCtxRef.current.state === "suspended") {
      await audioCtxRef.current.resume();
    }
    return audioCtxRef.current;
  }, []);

  const stopAudio = useCallback(() => {
    try {
      sourceRef.current?.stop();
    } catch {
      /* already stopped */
    }
    sourceRef.current?.disconnect();
    sourceRef.current = null;
    if (typeof window !== "undefined") window.speechSynthesis?.cancel();
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    rafRef.current = 0;
    setEnergy(0.12);
  }, []);

  const playBuffer = useCallback(
    async (pcm: ArrayBuffer, text: string) => {
      const ctx = await unlockAudio();
      if (!ctx) throw new Error("no audio context");
      const decoded = await ctx.decodeAudioData(pcm.slice(0));
      const src = ctx.createBufferSource();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      src.buffer = decoded;
      src.connect(analyser);
      analyser.connect(ctx.destination);
      sourceRef.current = src;
      const data = new Uint8Array(analyser.frequencyBinCount);
      const duration = Math.max(0.35, decoded.duration);
      await new Promise<void>((resolve, reject) => {
        let started = 0;
        const loop = () => {
          analyser.getByteTimeDomainData(data);
          let sum = 0;
          for (let i = 0; i < data.length; i++) {
            const v = (data[i] - 128) / 128;
            sum += v * v;
          }
          const rms = Math.sqrt(sum / data.length);
          setEnergy(0.22 + Math.min(0.78, rms * 6));
          const elapsed = ctx.currentTime - started;
          const n = Math.min(
            text.length,
            Math.max(1, Math.ceil((elapsed / duration) * text.length)),
          );
          setSpokenLine(text.slice(0, n));
          rafRef.current = requestAnimationFrame(loop);
        };
        src.onended = () => {
          if (rafRef.current) cancelAnimationFrame(rafRef.current);
          sourceRef.current = null;
          setSpokenLine(text);
          setEnergy(0.12);
          resolve();
        };
        try {
          src.start();
          started = ctx.currentTime;
          loop();
        } catch (err) {
          reject(err);
        }
      });
    },
    [unlockAudio],
  );

  const speakAnswer = useCallback(
    async (text: string) => {
      setState("speaking");
      setSpokenLine("");
      try {
        const pcm = await speak(text);
        await playBuffer(pcm, text);
        setState("idle");
        return;
      } catch {
        /* ElevenLabs blocked or failed — still speak via the browser. */
      }
      if (typeof window !== "undefined" && window.speechSynthesis) {
        await new Promise<void>((resolve) => {
          const utter = new SpeechSynthesisUtterance(text);
          utter.rate = 1.02;
          let i = 0;
          const tick = window.setInterval(() => {
            i = Math.min(text.length, i + 1);
            setSpokenLine(text.slice(0, i));
            setEnergy(0.28 + Math.random() * 0.55);
            if (i >= text.length) window.clearInterval(tick);
          }, 70);
          utter.onboundary = (ev) => {
            if (typeof ev.charIndex === "number") {
              setSpokenLine(text.slice(0, ev.charIndex + (ev.charLength || 1)));
            }
          };
          utter.onend = () => {
            window.clearInterval(tick);
            setSpokenLine(text);
            resolve();
          };
          utter.onerror = () => {
            window.clearInterval(tick);
            setSpokenLine(text);
            resolve();
          };
          window.speechSynthesis.speak(utter);
        });
        setState("idle");
        setEnergy(0.12);
        return;
      }
      setSpokenLine(text);
      setError("Could not play spoken audio. Check the ElevenLabs key and speaker.");
      setState("idle");
    },
    [playBuffer],
  );

  const runQuery = useCallback(
    async (query: string) => {
      const q = query.trim();
      if (!q) return;
      await unlockAudio();
      stopAudio();
      setError(null);
      setPartial("");
      setDraft("");
      setSpokenLine("");
      const userTurn: Turn = {
        id: crypto.randomUUID(),
        role: "user",
        text: q,
      };
      const vaaniId = crypto.randomUUID();
      setTurns((t) => [
        ...t,
        userTurn,
        { id: vaaniId, role: "vaani", text: "", partial: true },
      ]);
      setState("thinking");
      try {
        const result = await askStream(
          q,
          (tok, info) => {
            setTurns((prev) =>
              prev.map((turn) =>
                turn.id === vaaniId
                  ? {
                      ...turn,
                      text: info?.replace ? tok : turn.text + tok,
                    }
                  : turn,
              ),
            );
          },
          (meta) => {
            setLastResult((cur) => ({
              answer: meta.answer ?? cur?.answer ?? "",
              verdict: meta.verdict ?? cur?.verdict ?? "GROUNDED",
              language: meta.language ?? cur?.language ?? "en",
              citations: meta.citations ?? cur?.citations ?? [],
              timings: meta.timings ?? cur?.timings ?? [],
              rag_ms: meta.rag_ms ?? cur?.rag_ms ?? 0,
              ttft_ms: meta.ttft_ms ?? cur?.ttft_ms ?? null,
              refuse_reason: meta.refuse_reason ?? cur?.refuse_reason ?? null,
              tools: meta.tools ?? cur?.tools ?? [],
              model: meta.model ?? cur?.model ?? "",
            }));
          },
        );
        setLastResult(result);
        setTurns((prev) =>
          prev.map((turn) =>
            turn.id === vaaniId
              ? { ...turn, text: result.answer, partial: false, result }
              : turn,
          ),
        );
        if (result.answer) {
          await speakAnswer(result.answer);
        } else {
          setState("idle");
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "ask failed";
        setError(
          /failed to fetch|networkerror|network error|load failed/i.test(msg)
            ? "Could not reach the API. Keep make api running, then ask again."
            : msg,
        );
        setState("idle");
      }
    },
    [speakAnswer, stopAudio, unlockAudio],
  );

  const startListening = useCallback(async () => {
    setError(null);
    setPartial("");
    setState("listening");
    setEnergy(0.45);
    await unlockAudio();
    try {
      const token = await fetchScribeToken();
      if (token) {
        const { Scribe, CommitStrategy, RealtimeEvents } = await import(
          "@elevenlabs/client"
        );
        const conn = Scribe.connect({
          token,
          modelId: "scribe_v2_realtime",
          commitStrategy: CommitStrategy.VAD,
          includeLanguageDetection: true,
          microphone: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
        scribeRef.current = conn;
        conn.on(RealtimeEvents.PARTIAL_TRANSCRIPT, (data) => {
          const text = ("text" in data && data.text) || "";
          setPartial(String(text));
        });
        conn.on(RealtimeEvents.COMMITTED_TRANSCRIPT, (data) => {
          const text = String(("text" in data && data.text) || "").trim();
          conn.close();
          scribeRef.current = null;
          if (text) void runQuery(text);
        });
        conn.on(RealtimeEvents.ERROR, () => {
          setError("Scribe error — try typing, or use Chrome speech.");
        });
        return;
      }
    } catch {
      // Web Speech fallback
    }

    const w = window as unknown as {
      webkitSpeechRecognition?: new () => BrowserSpeech;
      SpeechRecognition?: new () => BrowserSpeech;
    };
    const SR = w.webkitSpeechRecognition || w.SpeechRecognition;
    if (!SR) {
      setError(
        "Voice needs ElevenLabs Scribe or Chrome speech recognition. Type below.",
      );
      setState("idle");
      return;
    }
    const rec = new SR();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = "en-IN";
    rec.onresult = (ev: {
      resultIndex: number;
      results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>;
    }) => {
      let text = "";
      let final = false;
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        text += ev.results[i][0].transcript;
        if (ev.results[i].isFinal) final = true;
      }
      setPartial(text);
      if (final) void runQuery(text);
    };
    rec.onerror = () => setState("idle");
    rec.start();
    recRef.current = rec;
  }, [runQuery, unlockAudio]);

  const stopListening = useCallback(() => {
    scribeRef.current?.commit();
    scribeRef.current?.close();
    scribeRef.current = null;
    recRef.current?.stop();
    recRef.current = null;
    if (state === "listening" && partial.trim()) {
      void runQuery(partial);
    } else if (state === "listening") {
      setState("idle");
      setEnergy(0.12);
    }
  }, [partial, runQuery, state]);

  return {
    state,
    turns,
    partial,
    energy,
    health,
    error,
    lastResult,
    spokenLine,
    draft,
    setDraft,
    startListening,
    stopListening,
    runQuery,
  };
}

type BrowserSpeech = {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((ev: {
    resultIndex: number;
    results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>;
  }) => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
};
