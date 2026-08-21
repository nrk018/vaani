"""Walk knowledge/ plus optional MSMARCO-XI samples into a passage list."""

from __future__ import annotations

import json
import re
from pathlib import Path

HEADING = re.compile(r"^#{1,3}\s+", re.M)


def repo_root() -> Path:
    here = Path(__file__).resolve().parent
    for cand in [here.parent, here, Path.cwd()]:
        if (cand / "knowledge").exists():
            return cand
    return here.parent


def _split_markdown(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"(?=^#{1,3}\s+)", text.strip(), flags=re.M)
    out: list[tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.splitlines()
        title = re.sub(r"^#+\s*", "", lines[0]).strip() if lines else "untitled"
        body = "\n".join(lines[1:]).strip() or part
        out.append((title, body))
    return out or [("document", text.strip())]


def load_goa_pack(root: Path | None = None) -> list[dict]:
    root = root or repo_root()
    passages: list[dict] = []
    goa = root / "knowledge" / "goa"
    if not goa.exists():
        return passages
    for path in sorted(goa.glob("*.md")):
        blocks = _split_markdown(path.read_text(encoding="utf-8"))
        for i, (title, body) in enumerate(blocks):
            passages.append(
                {
                    "id": f"goa-{path.stem}-{i:02d}",
                    "lang": "en",
                    "query_type": "DESCRIPTION",
                    "title": title,
                    "text": body,
                    "source": "goa",
                }
            )
    return passages


def load_seed_jsonl(root: Path | None = None) -> list[dict]:
    root = root or repo_root()
    path = root / "knowledge" / "seed" / "passages.jsonl"
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        row.setdefault("source", "seed")
        rows.append(row)
    return rows


# Hub parquet names (the published dataset only has BuilderConfig "default").
# Train files are ~3.7GB each; validation is the latency-safe slice for ingest-xi.
LANG_PARQUET = {
    "as": "validation/asmval.parquet",
    "bn": "validation/benval.parquet",
    "gu": "validation/gujval.parquet",
    "hi": "validation/hinval.parquet",
    "kn": "validation/kanval.parquet",
    "ml": "validation/malval.parquet",
    "mr": "validation/marval.parquet",
    "ne": "validation/nepval.parquet",
    "or": "validation/orival.parquet",
    "pa": "validation/panval.parquet",
    "sa": "validation/sanval.parquet",
    "ta": "validation/tamval.parquet",
    "te": "validation/telval.parquet",
    "ur": "validation/urdval.parquet",
}

LANG_FLORES = {
    "as": "asm",
    "bn": "ben",
    "gu": "guj",
    "hi": "hin",
    "kn": "kan",
    "ml": "mal",
    "mr": "mar",
    "ne": "nep",
    "or": "ori",
    "pa": "pan",
    "sa": "san",
    "ta": "tam",
    "te": "tel",
    "ur": "urd",
}


def _xi_stream(lang: str):
    from datasets import load_dataset
    from dotenv import load_dotenv
    from huggingface_hub import hf_hub_download

    load_dotenv(repo_root() / ".env")
    parquet = LANG_PARQUET.get(lang)
    print(f"downloading MSMARCO-XI {lang} ({parquet or 'default'})…", flush=True)
    if parquet:
        local = hf_hub_download(
            repo_id="ai4bharat/MSMARCO-XI",
            filename=parquet,
            repo_type="dataset",
        )
        print(f"cached {lang} at {local}", flush=True)
        return load_dataset("parquet", data_files=local, split="train", streaming=True)
    return load_dataset("ai4bharat/MSMARCO-XI", split="train", streaming=True)


def _lang_match(row: dict, lang: str) -> bool:
    target = (row.get("target_lang") or "").lower()
    if not target:
        return True
    needles = {lang, LANG_FLORES.get(lang, lang)}
    return any(n in target for n in needles)


def sample_msmarco_xi(
    languages: tuple[str, ...] = ("hi",),
    max_rows: int = 4000,
    prefer_selected: bool = True,
) -> list[dict]:
    """Stream a slice of MSMARCO-XI (hi/mr validation).

    Full dump is ~11M rows / 55GB — do not index it. `max_rows` is a
    query budget split across languages (selected passages only).
    """
    try:
        from datasets import load_dataset  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("Install datasets to sample MSMARCO-XI") from exc

    out: list[dict] = []
    seen: set[str] = set()
    per_lang = max(1, max_rows // max(len(languages), 1))
    for lang in languages:
        ds = _xi_stream(lang)
        taken = 0
        for row in ds:
            if not _lang_match(row, lang):
                continue
            qtype = row.get("query_type") or "DESCRIPTION"
            passages = row.get("passages") or {}
            selected = list(passages.get("is_selected") or [])
            english = list(passages.get("English_passages") or [])
            translated = list(passages.get("Translated_passages") or [])
            qid = row.get("query_id")
            qtext = (row.get("Eng_Query") or row.get("query") or "").strip()
            for i, (en, tr) in enumerate(zip(english, translated)):
                is_sel = bool(selected[i]) if i < len(selected) else False
                if prefer_selected and not is_sel:
                    continue
                for lang_code, text in (("en", en), (lang, tr)):
                    text = (text or "").strip()
                    if len(text) < 40:
                        continue
                    key = text[:240]
                    if key in seen:
                        continue
                    seen.add(key)
                    body = text if not qtext else f"{qtext}\n{text}"
                    out.append(
                        {
                            "id": f"xi-{lang}-{qid}-{i}-{lang_code}",
                            "lang": lang_code,
                            "query_type": qtype,
                            "title": qtext[:80] or "msmarco-xi",
                            "text": body,
                            "source": "msmarco-xi",
                            "is_selected": is_sel,
                        }
                    )
            taken += 1
            if taken % 100 == 0:
                print(f"  {lang}: {taken}/{per_lang} queries → {len(out)} passages", flush=True)
            if taken >= per_lang:
                break
        print(f"  {lang} done: {taken} queries, {len(out)} passages so far", flush=True)
    return out


def load_all_local() -> list[dict]:
    return load_goa_pack() + load_seed_jsonl()
