import { Nav } from "@/components/Nav";

export default function AboutPage() {
  return (
    <>
      <Nav active="about" />
      <main className="mx-auto max-w-3xl px-6 pb-24 pt-24">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-sea/80">
          HH Goa 2026 · Task 2
        </p>
        <h1 className="mt-3 font-serif text-5xl leading-tight text-white md:text-6xl">
          A living voice that only speaks from evidence.
        </h1>
        <p className="mt-6 text-lg leading-relaxed text-white/65">
          Vaani (वाणी) is a voice-enabled RAG system. You speak. ElevenLabs
          Scribe transcribes. A hybrid index retrieves from MSMARCO-XI (English,
          Hindi, Marathi) and a Goa knowledge pack. A harnessed generator
          answers only when the passages support it. ElevenLabs Flash speaks
          back.
        </p>

        <section className="mt-14 space-y-8">
          <Block title="Pipeline">
            Voice → Scribe v2 Realtime → inbound guard → hybrid retrieve (dense
            HNSW + BM25, RRF) → parent expand → Groq generate → outbound
            faithfulness check → streaming TTS.
          </Block>
          <Block title="Chunking (offline, four strategies)">
            Native MS MARCO passages. Parent–child windows (~100 tokens, 20
            overlap). Semantic sentence groups with overlap. Proposition slices
            for factoid queries. Query time never chunks — that is how the 200ms
            budget stays possible.
          </Block>
          <Block title="Harness">
            Structured graph: normalize, inbound_guard, retrieve, ground,
            generate, outbound_guard, emit. One retrieve retry, one generate
            retry, hard refusal instead of hanging. Every node is timed.
          </Block>
          <Block title="Guardrails">
            Jailbreak and unsafe filters. Retrieval floor. Answer-to-passage
            token overlap. Off-corpus questions (weather, sports scores, private
            data) are refused in the user&apos;s language.
          </Block>
          <Block title="Goa">
            MSMARCO-XI has no Konkani split. Vaani indexes Marathi as the
            nearest Indic neighbor and keeps a first-class Goa pack — HH Goa,
            Panaji, feni, Dev borem korum — so the product has a place, not just
            a dataset.
          </Block>
        </section>
      </main>
    </>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="font-serif text-2xl text-gold">{title}</h2>
      <p className="mt-2 leading-relaxed text-white/60">{children}</p>
    </div>
  );
}
