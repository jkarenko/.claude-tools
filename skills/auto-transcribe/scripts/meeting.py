#!/usr/bin/env python3
"""
End-to-end meeting transcription for mono or stereo meeting recordings.

The channel layout is configurable (settings: diarization.user_channel, CLI:
--user-channel): a stereo recording can carry the user's own microphone on one
channel ("left" or "right") with everyone else on the other. Without a dedicated
user channel (mono files, plain stereo mixes, or user_channel unset) the whole
recording is treated as a single multi-speaker channel.

Pipeline
  1. split channels (ffmpeg) -> 16 kHz mono wavs; internally "left" always means
     the user's own channel regardless of its physical side, "right" everyone else
  2. Whisper (mlx) per channel, language forced (default from settings), word timestamps
  3. multi-speaker channel: split Whisper segments at pauses, ECAPA speaker embeddings,
     agglomerative clustering -> "Speaker 1..N"; match clusters against the
     speaker profile store (global, biased by --attendees and filename context)
  4. merge both channels by time, write next to the audio file:
       <stem>.transcript.json   everything (raw segments, embeddings, speakers)
       <stem>.md                readable speaker-labelled transcript
       <stem>.speakers.yaml     review sheet: edit names, then `rename`
  5. `rename`: apply names (from CLI mapping and/or the yaml), re-render the .md,
     enrol the confirmed speakers' centroids into the profile store.

Commands
  meeting.py run <audio> [-l fi] [--num-speakers N] [--attendees "A,B"] [--threshold T] [--force]
  meeting.py rediarize <audio|json> [--num-speakers N] [--threshold T] [--attendees ...]
  meeting.py rename <audio|json> ["Speaker 1=Name, Speaker 2=Other"] [--no-enrol]
  meeting.py speakers [list | forget <name>]

Environment check (no venv needed): python3 scripts/doctor.py
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from utils.config import MODELS_DIR, load_settings, load_vocabulary, update_setting  # noqa: E402
from utils.domain import (  # noqa: E402
    DEFAULT_FUZZY,
    DOMAIN_DIR,
    load_domain,
    normalize_text,
    resolve_packs,
)
from utils.speakers import (  # noqa: E402
    ECAPA_MODEL,
    add_centroid,
    context_tokens,
    cosine,
    delete_profile,
    list_profiles,
    match_embedding,
)

SR = 16000
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg", ".mp4", ".mov"}

# Label for the user's own-mic channel until their name is configured
# (diarization.user_name) or learned via `rename`.
USER_PLACEHOLDER = "You"

DEFAULT_PROMPT = (
    "tiimi, projekti, asiakas, sprintti, daily, tiketti, backlog, "
    "tuotanto, testaus, integraatio, rajapinta, API, Azure, AWS, SharePoint, Slack, "
    "Jira, Confluence, PowerPoint, Teams, tekoäly, Claude, Copilot."
)
# Whisper's Finnish near-silence tics — dropped when the segment is short.
TIC_PATTERNS = [
    r"kiitos[.!]?", r"kiitos katsomisesta[.!]?", r"tekstitys.*", r"tekstitykset.*",
    r"suomen ?tekstitys.*", r"sub(title)?s? by .*", r"thank you[.!]?", r"okei[.!]?",
]


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------

def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def ts(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int(seconds % 3600 // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:05.2f}"


def ts_short(seconds: float) -> str:
    seconds = max(0.0, seconds)
    return f"{int(seconds // 3600):02d}:{int(seconds % 3600 // 60):02d}:{int(seconds % 60):02d}"


def parse_filename(path: Path, org_marker: Optional[str] = None) -> dict:
    """'20260819 1130 Acme - CustomerX - ProjectY - dev daily.mp3' -> date/time/context.

    `org_marker` (settings: filename.org_marker) also strips a leading employer
    name that is not followed by a dash ("Acme weekly" -> "weekly")."""
    m = re.match(r"^(\d{8})[ _](\d{4})[ _]+(.*)$", path.stem)
    info = {"recorded_at": None, "context": path.stem, "org": None}
    if m:
        d, t, rest = m.groups()
        try:
            info["recorded_at"] = datetime.strptime(d + t, "%Y%m%d%H%M").isoformat(timespec="minutes")
        except ValueError:
            pass
        rest = rest.strip()
        # strip the leading employer marker ("<Org> - " / "<Org> ")
        mm = re.match(r"^([A-Za-z0-9]+)\s*[-–]\s*(.*)$", rest)
        if mm:
            info["org"], rest = mm.group(1), mm.group(2)
        elif org_marker and rest.lower().startswith(org_marker.lower() + " "):
            info["org"], rest = rest[:len(org_marker)], rest[len(org_marker) + 1:]
        info["context"] = rest.strip()
    info["context_parts"] = [p.strip() for p in re.split(r"\s[-–]\s", info["context"]) if p.strip()]
    info["context_tokens"] = sorted(context_tokens(info["context"]))
    return info


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=channels,sample_rate",
         "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    ch = int(j["streams"][0].get("channels", 1))
    return {"duration": float(j["format"]["duration"]), "channels": ch}


def split_channels(src: Path, workdir: Path, user_channel: Optional[str]) -> dict[str, Path]:
    """Return {'left': user wav, 'right': others wav} or {'mono': wav} at 16 kHz mono PCM.

    Keys are semantic, not physical: 'left' is always the user's own mic channel —
    even when user_channel='right' puts it on the physically right channel — and
    'right' is everyone else. With no dedicated user channel (user_channel None)
    the recording is downmixed to one multi-speaker 'mono' channel."""
    if user_channel in ("left", "right"):
        user, others = workdir / "left.wav", workdir / "right.wav"
        u, o = ("[l]", "[r]") if user_channel == "left" else ("[r]", "[l]")
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex",
             f"[0:a]channelsplit=channel_layout=stereo[L][R];[L]aresample={SR}[l];[R]aresample={SR}[r]",
             "-map", u, "-ac", "1", "-c:a", "pcm_s16le", str(user),
             "-map", o, "-ac", "1", "-c:a", "pcm_s16le", str(others)], check=True)
        return {"left": user, "right": others}
    mono = workdir / "mono.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", str(SR),
                    "-c:a", "pcm_s16le", str(mono)], check=True)
    return {"mono": mono}


def load_wav(path: Path) -> np.ndarray:
    import soundfile as sf
    audio, sr = sf.read(str(path), dtype="float32")
    assert sr == SR, f"expected {SR} Hz, got {sr}"
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio


# ----------------------------------------------------------------------------
# transcription
# ----------------------------------------------------------------------------

def whisper_channel(wav: Path, language: str, model: str, prompt: str, task: str = "transcribe") -> dict:
    import mlx_whisper
    return mlx_whisper.transcribe(
        str(wav),
        path_or_hf_repo=model,
        language=None if language == "auto" else language,
        task=task,
        word_timestamps=True,
        initial_prompt=prompt or None,
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
        logprob_threshold=-1.0,
        compression_ratio_threshold=2.4,
        hallucination_silence_threshold=2.0,
        verbose=None,  # None = no progress bar, no per-segment print
    )


def is_tic(text: str, duration: float, total: float, start: float) -> bool:
    t = text.strip().lower()
    if duration >= 2.0:
        return False
    # genuine goodbyes live in the last minute
    if total - start < 60 and re.fullmatch(r"kiitos[.!]?", t):
        return False
    return any(re.fullmatch(p, t) for p in TIC_PATTERNS)


def clean_segments(raw: dict, total: float) -> list[dict]:
    out = []
    for s in raw.get("segments", []):
        text = s.get("text", "").strip()
        if not text:
            continue
        dur = s["end"] - s["start"]
        if s.get("no_speech_prob", 0) > 0.85 and s.get("avg_logprob", 0) < -1.0:
            continue
        if is_tic(text, dur, total, s["start"]):
            continue
        words = [{"w": w["word"], "s": round(w["start"], 2), "e": round(w["end"], 2),
                  "p": round(w.get("probability", 0.0), 3)} for w in s.get("words", [])]
        out.append({"start": round(s["start"], 2), "end": round(s["end"], 2), "text": text,
                    "words": words, "avg_logprob": round(s.get("avg_logprob", 0.0), 3),
                    "no_speech_prob": round(s.get("no_speech_prob", 0.0), 3)})
    return out


# ----------------------------------------------------------------------------
# diarization of one channel
# ----------------------------------------------------------------------------

def split_at_pauses(seg: dict, min_gap: float = 0.7) -> list[dict]:
    """Split a Whisper segment into units at word gaps >= min_gap."""
    words = seg.get("words") or []
    if len(words) < 2:
        return [dict(seg)]
    units, cur = [], [words[0]]
    for prev, w in zip(words, words[1:]):
        if w["s"] - prev["e"] >= min_gap:
            units.append(cur)
            cur = [w]
        else:
            cur.append(w)
    units.append(cur)
    if len(units) == 1:
        return [dict(seg)]
    out = []
    for ws in units:
        out.append({"start": ws[0]["s"], "end": ws[-1]["e"],
                    "text": "".join(w["w"] for w in ws).strip(), "words": ws,
                    "avg_logprob": seg.get("avg_logprob"), "no_speech_prob": seg.get("no_speech_prob")})
    return out


class Embedder:
    def __init__(self):
        import torch
        from speechbrain.inference.speaker import EncoderClassifier
        self.torch = torch
        self.enc = EncoderClassifier.from_hparams(
            source=ECAPA_MODEL, savedir=str(MODELS_DIR / "ecapa"), run_opts={"device": "cpu"})

    def embed(self, audio: np.ndarray) -> Optional[np.ndarray]:
        if len(audio) < int(0.4 * SR):
            return None
        win, hop = int(1.5 * SR), int(0.75 * SR)
        chunks = [audio] if len(audio) <= win else [audio[i:i + win] for i in range(0, len(audio) - win + 1, hop)]
        embs = []
        with self.torch.no_grad():
            for c in chunks:
                e = self.enc.encode_batch(self.torch.from_numpy(np.ascontiguousarray(c)).unsqueeze(0))
                e = e.squeeze().numpy()
                embs.append(e / (np.linalg.norm(e) + 1e-9))
        m = np.mean(embs, axis=0)
        return m / (np.linalg.norm(m) + 1e-9)


def embed_units(segments: list[dict], audio: np.ndarray, embedder: Embedder) -> list[dict]:
    """Split segments at pauses and attach an ECAPA embedding to each unit."""
    units = []
    for seg in segments:
        units.extend(split_at_pauses(seg))
    units.sort(key=lambda u: u["start"])
    for u in units:
        u["emb"] = embedder.embed(audio[int(u["start"] * SR):int(u["end"] * SR)])
    return units


def cluster_units(
    units: list[dict],
    *,
    num_speakers: Optional[int],
    threshold: float,
    min_unit: float = 2.0,
    absorb_seconds: float = 20.0,
    absorb_sim: float = 0.40,
) -> dict:
    """Assign `cluster` (0..N-1, ordered by talk time) to every unit in place.

    - only units >= min_unit s with an embedding take part in clustering
      (short backchannels have noisy embeddings and would split off on their own)
    - shorter / unembeddable units go to the nearest centroid (cos >= 0.3), else to
      the temporally nearest labelled unit
    - minor clusters (< absorb_seconds of speech) are merged into the most similar
      larger cluster when that similarity >= absorb_sim — i.e. when it looks like the
      same voice; a quiet but distinct attendee is kept
    Returns {cluster_id: {seconds, turns, centroid}}.
    """
    for u in units:
        u.pop("cluster", None)
    idx = [i for i, u in enumerate(units) if u.get("emb") is not None and (u["end"] - u["start"]) >= min_unit]
    if not idx:  # nothing robust to cluster on: fall back to anything embeddable
        idx = [i for i, u in enumerate(units) if u.get("emb") is not None]
    if not idx:
        for u in units:
            u["cluster"] = 0
        return {0: {"seconds": sum(u["end"] - u["start"] for u in units), "turns": len(units), "centroid": None}}

    X = np.stack([units[i]["emb"] for i in idx])
    if len(idx) == 1:
        labels = np.array([0])
    else:
        from sklearn.cluster import AgglomerativeClustering
        if num_speakers:
            cl = AgglomerativeClustering(n_clusters=min(num_speakers, len(idx)), metric="cosine", linkage="average")
        else:
            cl = AgglomerativeClustering(n_clusters=None, distance_threshold=threshold, metric="cosine", linkage="average")
        labels = cl.fit_predict(X)
    for i, lab in zip(idx, labels):
        units[i]["cluster"] = int(lab)

    def stats():
        c, sec = {}, {}
        for i in idx:
            k = units[i]["cluster"]
            c.setdefault(k, []).append(units[i]["emb"])
            sec[k] = sec.get(k, 0.0) + (units[i]["end"] - units[i]["start"])
        cents = {}
        for k, v in c.items():
            m = np.mean(v, axis=0)
            cents[k] = m / (np.linalg.norm(m) + 1e-9)
        return cents, sec

    if not num_speakers:
        while True:
            cents, sec = stats()
            if len(cents) <= 1:
                break
            merged = False
            for k in sorted(sec, key=lambda k: sec[k]):
                if sec[k] >= absorb_seconds:
                    break
                bigger = {kk: v for kk, v in cents.items() if kk != k and sec[kk] > sec[k]}
                if not bigger:
                    continue
                tgt = max(bigger, key=lambda kk: cosine(cents[k], bigger[kk]))
                if cosine(cents[k], bigger[tgt]) >= absorb_sim:
                    for i in idx:
                        if units[i]["cluster"] == k:
                            units[i]["cluster"] = tgt
                    merged = True
                    break
            if not merged:
                break

    cents, _ = stats()
    for j, u in enumerate(units):
        if "cluster" in u:
            continue
        if u.get("emb") is not None and cents:
            best = max(cents, key=lambda k: cosine(u["emb"], cents[k]))
            if cosine(u["emb"], cents[best]) >= 0.3:
                u["cluster"] = best
                continue
        prev_c = next((units[k]["cluster"] for k in range(j - 1, -1, -1) if "cluster" in units[k]), None)
        next_c = next((units[k]["cluster"] for k in range(j + 1, len(units)) if "cluster" in units[k]), None)
        u["cluster"] = prev_c if prev_c is not None else (next_c if next_c is not None else 0)

    # smoothing: a < 1.5 s unit sandwiched between same-speaker units takes that speaker
    for j in range(1, len(units) - 1):
        a, b, c = units[j - 1], units[j], units[j + 1]
        if a["cluster"] == c["cluster"] != b["cluster"] and (b["end"] - b["start"]) < 1.5:
            b["cluster"] = a["cluster"]

    talk = {}
    for u in units:
        talk[u["cluster"]] = talk.get(u["cluster"], 0.0) + (u["end"] - u["start"])
    order = sorted(talk, key=lambda k: talk[k], reverse=True)
    remap = {old: new for new, old in enumerate(order)}
    for u in units:
        u["cluster"] = remap[u["cluster"]]
    clusters = {}
    for old, new in remap.items():
        embs = [u["emb"] for u in units if u["cluster"] == new and u.get("emb") is not None
                and (u["end"] - u["start"]) >= min_unit]
        if not embs:
            embs = [u["emb"] for u in units if u["cluster"] == new and u.get("emb") is not None]
        cent = None
        if embs:
            cent = np.mean(embs, axis=0)
            cent = cent / (np.linalg.norm(cent) + 1e-9)
        clusters[new] = {"seconds": talk[old], "centroid": cent,
                         "turns": sum(1 for u in units if u["cluster"] == new)}
    return clusters


def diarize_channel(segments, audio, embedder, *, num_speakers, threshold, min_unit: float = 2.0):
    units = embed_units(segments, audio, embedder)
    clusters = cluster_units(units, num_speakers=num_speakers, threshold=threshold, min_unit=min_unit)
    return units, clusters


# ----------------------------------------------------------------------------
# speakers, rendering, review sheet
# ----------------------------------------------------------------------------

# Two enrolled voices both matching one cluster this strongly / this close together
# is the signature of a merged cluster (two people fused by the clustering cut).
MERGE_SUSPECT = 0.70
MERGE_MARGIN = 0.06


def guess_names(clusters: dict, attendees: list[str], context: str, auto_threshold: float,
                exclude: Optional[set] = None, display_floor: float = 0.35) -> dict:
    """Return {cluster_id: {'label', 'guess': [...], 'auto': bool, 'name', 'ambiguous'}}.

    `exclude` = names that cannot be on this channel (the user, when their mic has its own channel).
    Guesses below `display_floor` raw cosine are not shown at all.
    `ambiguous` = [name_a, name_b] when two enrolled voices tie on the cluster —
    a merged-cluster symptom; such clusters are never auto-labelled.
    """
    out = {}
    candidates = {}
    exclude = {e.lower() for e in (exclude or set())}
    for cid, c in clusters.items():
        label = f"Speaker {cid + 1}"
        ranked = []
        if c["centroid"] is not None:
            ranked = [r for r in match_embedding(c["centroid"], attendees=attendees, context=context, top_k=6)
                      if r["name"].lower() not in exclude and r["score"] >= display_floor][:3]
        out[cid] = {"label": label, "guess": ranked, "auto": False, "name": None, "ambiguous": None}
        if ranked:
            candidates[cid] = ranked[0]
    # auto-apply confident, unambiguous guesses (one cluster per name)
    taken = {}
    for cid, best in sorted(candidates.items(), key=lambda kv: kv[1]["adjusted"], reverse=True):
        if best["score"] < auto_threshold or best["name"] in taken:
            continue
        second = next((r for r in out[cid]["guess"][1:] if r["name"] != best["name"]), None)
        if second and second["score"] >= max(MERGE_SUSPECT, best["score"] - MERGE_MARGIN):
            out[cid]["ambiguous"] = [best["name"], second["name"]]
            continue
        if best.get("weak"):
            continue  # a weak (short-speech) voiceprint can hint but not auto-label
        out[cid]["name"] = best["name"]
        out[cid]["auto"] = True
        taken[best["name"]] = cid
    return out


def try_split_merged(units: list[dict], clusters: dict, names: dict, *, orig_n: Optional[int],
                     threshold: float, attendees: list[str], context: str, auto_thr: float,
                     floor: float, exclude: Optional[set]) -> tuple[dict, dict, Optional[str]]:
    """When a cluster ties two enrolled voices, retry finer clusterings (n+1..n+4)
    until those voices land on separate clusters. Falls back to the original
    clustering (with the ambiguity still flagged) when no split resolves it."""
    susp = {cid: v["ambiguous"] for cid, v in names.items() if v.get("ambiguous")}
    if not susp:
        return clusters, names, None
    base_n = len(clusters)
    for n in range(base_n + 1, base_n + 5):
        cl2 = cluster_units(units, num_speakers=n, threshold=threshold)
        nm2 = guess_names(cl2, attendees, context, auto_thr, exclude=exclude, display_floor=floor)
        if any(v.get("ambiguous") for v in nm2.values()):
            continue
        def has_top(name):
            return any(v["guess"] and v["guess"][0]["name"] == name
                       and v["guess"][0]["score"] >= MERGE_SUSPECT for v in nm2.values())
        if all(has_top(a) and has_top(b) for a, b in susp.values()):
            pairs = "; ".join(" / ".join(p) for p in susp.values())
            return cl2, nm2, (f"suspected merged cluster ({pairs} tied) — re-clustered at n={n}, "
                              "voices separated")
    # restore the original clustering (the attempts relabelled units in place)
    cl0 = cluster_units(units, num_speakers=orig_n, threshold=threshold)
    nm0 = guess_names(cl0, attendees, context, auto_thr, exclude=exclude, display_floor=floor)
    pairs = "; ".join(" / ".join(p) for p in susp.values())
    return cl0, nm0, (f"WARNING: a cluster matches two enrolled voices ({pairs}) and may merge two "
                      f"speakers — automatic split failed; try `rediarize -n {base_n + 1}` or a lower -t")


# A phrase of >= 6 chars repeated identically 4+ times in a row is a Whisper
# hallucination loop ("Siellä ollaan. Siellä ollaan. …"), not speech.
_REPEAT_RX = re.compile(r"(?P<ph>\S[^.!?]{4,}?[.!?]?)(?P<reps>(?:\s+(?P=ph)){3,})")


def collapse_repeats(text: str) -> str:
    def repl(m):
        n = 1 + m.group("reps").count(m.group("ph"))
        return f"{m.group('ph')} [×{n}]"
    return _REPEAT_RX.sub(repl, text)


def coalesce(segments: list[dict], gap: float = 1.5) -> list[dict]:
    turns = []
    for s in sorted(segments, key=lambda x: (x["start"], x["end"])):
        if turns and turns[-1]["speaker"] == s["speaker"] and s["start"] - turns[-1]["end"] < gap:
            turns[-1]["end"] = max(turns[-1]["end"], s["end"])
            turns[-1]["text"] += " " + s["text"]
        else:
            turns.append({"start": s["start"], "end": s["end"], "speaker": s["speaker"], "text": s["text"]})
    for t in turns:
        t["text"] = collapse_repeats(t["text"])
    return turns


def render_markdown(doc: dict) -> str:
    name_of = {k: (v.get("name") or k) for k, v in doc["speakers"].items()}
    segs = [{"start": s["start"], "end": s["end"], "speaker": name_of.get(s["speaker"], s["speaker"]),
             "text": s["text"]} for s in doc["segments"]]
    turns = coalesce(segs)
    src = Path(doc["source"]).name
    lines = [f"# {Path(doc['source']).stem}", ""]
    meta = []
    if doc.get("recorded_at"):
        meta.append(f"Recorded {doc['recorded_at'].replace('T', ' ')}")
    meta.append(f"duration {ts_short(doc['duration'])}")
    meta.append(f"transcribed {doc['created'][:10]} ({doc['model'].split('/')[-1]}, lang={doc['language']}"
                + (", translated to English" if doc.get("task") == "translate" else "") + ")")
    lines.append("; ".join(meta) + ".")
    lines.append("")
    lines.append("**Speakers:** " + ", ".join(
        f"{name_of[k]}" + (" (own mic)" if v.get("channel") == "left" else "") +
        (f" [{k}]" if v.get("name") and v["name"] != k else "") + f" — {v['seconds'] / 60:.1f} min"
        for k, v in doc["speakers"].items()))
    lines.append("")
    for t in turns:
        lines.append(f"**[{ts(t['start'])}–{ts(t['end'])}] {t['speaker']}:** {t['text']}")
        lines.append("")
    return "\n".join(lines)


def unmatched_attendees(doc: dict) -> list[str]:
    """Attendees who are neither assigned to nor guessed for any cluster.

    Elimination hint: with the others accounted for, an unidentified cluster is
    probably one of these (often a quiet attendee with no stored voiceprint)."""
    accounted = set()
    for v in doc["speakers"].values():
        if v.get("name"):
            accounted.add(v["name"].lower())
        for g in v.get("guess") or []:
            accounted.add(g["name"].lower())
    return [a for a in doc.get("attendees", []) if a.lower() not in accounted]


def speaker_samples(doc: dict, key: str, n_first: int = 3, n_long: int = 3) -> tuple[list, list]:
    segs = [s for s in doc["segments"] if s["speaker"] == key]
    turns = coalesce([{"start": s["start"], "end": s["end"], "speaker": key, "text": s["text"]} for s in segs])
    substantive = [t for t in turns if len(t["text"].split()) >= 6] or turns
    first = substantive[:n_first]
    seen = {id(t) for t in first}
    longest = [t for t in sorted(turns, key=lambda t: len(t["text"]), reverse=True) if id(t) not in seen][:n_long]
    return first, longest


def write_review_yaml(doc: dict, path: Path) -> None:
    src = Path(doc["source"])
    L = [f"# Speaker review sheet for: {src.name}",
         "# Fill in real names (or leave blank / keep 'Speaker N'), then run:",
         f'#   meeting.py rename "{src}"',
         "# Or pass a mapping directly:",
         f'#   meeting.py rename "{src}" "Speaker 1=Etunimi Sukunimi, Speaker 2=Toinen Nimi"',
         "# Lines starting with '#' are ignored. Blank = leave as is, '-' = clear the name.",
         "# Named speakers are enrolled into the global speaker store",
         "# (>= 20 s of speech as full voiceprints, 8-20 s as weak hint-only voiceprints).",
         ""]
    if doc.get("attendees"):
        L.append(f"# attendees hint: {', '.join(doc['attendees'])}")
    missing = unmatched_attendees(doc)
    if missing:
        L.append(f"# attendees not matched to any cluster: {', '.join(missing)}")
        L.append("#   an unidentified cluster below may be them — check the samples; a previous")
        L.append("#   meeting's .transcript.json centroids can identify a voice not in the store")
    L.append(f"# context: {doc.get('context', '')}")
    L.append("")
    L.append("speakers:")
    for key, v in doc["speakers"].items():
        if v.get("channel") == "left":
            hint = ("" if (v.get("name") or key) != USER_PLACEHOLDER
                    else " | put your real name here — it is remembered and your voice enrolled")
            L.append(f"  \"{key}\": \"{v.get('name') or ''}\"   # your own mic channel — {v['seconds'] / 60:.1f} min{hint}")
            continue
        guess = v.get("guess") or []
        g = ", ".join(f"{r['name']} {r['score']:.2f}" + (" (weak)" if r.get("weak") else "")
                      + (f" (+{r['bonus']:.2f} {r['why']})" if r.get("bonus") else "")
                      for r in guess[:3]) or "no match in store"
        tag = "auto " if v.get("auto") else ""
        minor = " | MINOR (<30 s; may be fragments)" if v["seconds"] < 30 else ""
        L.append(f"  \"{key}\": \"{v.get('name') or ''}\"   # {tag}guess: {g} | {v['seconds'] / 60:.1f} min, {v['turns']} turns{minor}")
        if v.get("ambiguous"):
            L.append(f"  # ^ WARNING: {' and '.join(v['ambiguous'])} tie on this cluster — it may merge "
                     "two speakers; check the samples or run rediarize with a higher -n")
    L.append("")
    L.append("# ---- samples (for identification) ----")
    for key, v in doc["speakers"].items():
        if v.get("channel") == "left":
            continue
        first, longest = speaker_samples(doc, key)
        L.append(f"# {key}: {v['seconds'] / 60:.1f} min, {v['turns']} turns")
        L.append("#   first:")
        for t in first:
            L.append(f"#     [{ts_short(t['start'])}] {t['text'][:220]}")
        L.append("#   longest:")
        for t in longest:
            L.append(f"#     [{ts_short(t['start'])}] {t['text'][:220]}")
        L.append("#")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def read_review_yaml(path: Path) -> dict[str, str]:
    import yaml
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sp = data.get("speakers") or {}
    return {str(k): (str(v).strip() if v is not None else "") for k, v in sp.items()}


def out_paths(audio_or_json: Path) -> dict[str, Path]:
    p = Path(audio_or_json)
    if p.suffix == ".json" and p.name.endswith(".transcript.json"):
        stem = p.name[: -len(".transcript.json")]
        base = p.parent / stem
    else:
        base = p.with_suffix("")
    return {"json": base.parent / f"{base.name}.transcript.json",
            "md": base.parent / f"{base.name}.md",
            "yaml": base.parent / f"{base.name}.speakers.yaml"}


def emb_list(e: Optional[np.ndarray]) -> Optional[list]:
    return None if e is None else [round(float(x), 4) for x in e]


# ----------------------------------------------------------------------------
# commands
# ----------------------------------------------------------------------------

def assemble_doc(doc: dict, units_by_channel: dict, clusters: dict, names: dict, user_name: str) -> dict:
    """Fill doc['speakers'] and doc['segments'] from per-channel units."""
    speakers = {}
    segments = []
    if "left" in units_by_channel:
        lu = units_by_channel["left"]
        speakers[user_name] = {"channel": "left", "name": user_name,
                               "seconds": round(sum(u["end"] - u["start"] for u in lu), 1),
                               "turns": len(lu), "centroid": None}
        for u in lu:
            segments.append({"start": u["start"], "end": u["end"], "channel": "left", "speaker": user_name,
                             "text": u["text"], "words": u.get("words", []),
                             "avg_logprob": u.get("avg_logprob"), "no_speech_prob": u.get("no_speech_prob")})
    multi_ch = "right" if "right" in units_by_channel else "mono"
    mu = units_by_channel.get(multi_ch, [])
    for cid in sorted(clusters):
        key = f"Speaker {cid + 1}"
        c = clusters[cid]
        speakers[key] = {"channel": multi_ch, "name": names[cid]["name"], "auto": names[cid]["auto"],
                         "guess": names[cid]["guess"], "ambiguous": names[cid].get("ambiguous"),
                         "seconds": round(c["seconds"], 1),
                         "turns": c["turns"], "centroid": emb_list(c["centroid"])}
    for u in mu:
        segments.append({"start": u["start"], "end": u["end"], "channel": multi_ch,
                         "speaker": f"Speaker {u['cluster'] + 1}", "text": u["text"],
                         "words": u.get("words", []), "emb": emb_list(u.get("emb")),
                         "avg_logprob": u.get("avg_logprob"), "no_speech_prob": u.get("no_speech_prob")})
    segments.sort(key=lambda s: (s["start"], s["end"]))
    doc["speakers"] = speakers
    doc["segments"] = segments
    return doc


def cmd_run(args) -> None:
    settings = load_settings()
    src = Path(args.audio).expanduser().resolve()
    if not src.exists():
        sys.exit(f"not found: {src}")
    paths = out_paths(src)
    if paths["json"].exists() and not args.force:
        sys.exit(f"{paths['json'].name} exists — use --force to redo, or `rediarize` / `rename`.")

    lang = args.language or settings["transcription"].get("language", "auto")
    task = getattr(args, "task", None) or "transcribe"
    model = settings["transcription"]["model"]
    dia = settings.get("diarization", {})
    user_name = dia.get("user_name") or USER_PLACEHOLDER
    threshold = args.threshold if args.threshold is not None else float(dia.get("cluster_threshold", 0.55))
    auto_thr = float(dia.get("auto_label_threshold", 0.70))
    guess_floor = float(dia.get("guess_display_threshold", 0.35))
    attendees = [a.strip() for a in (args.attendees or "").split(",") if a.strip()]
    # known names first: they bias Whisper toward the right spellings.
    # Domain canonicals outrank the generic vocabulary — initial_prompt is
    # capped (224 tokens) and silently truncated, so whatever matters most has
    # to come first. Biasing only helps the *first* time a term is heard;
    # `meeting.py normalize` is what repairs the confident repeats.
    known_names = ([user_name] if user_name != USER_PLACEHOLDER else []) + attendees

    info = probe(src)
    meta = parse_filename(src, org_marker=settings.get("filename", {}).get("org_marker"))
    packs = resolve_packs(set(meta.get("context_tokens") or []), parse_list(args.domain))
    domain_terms = [t.canonical for t in load_domain(packs)]
    seen = {d.lower() for d in domain_terms}
    extra = domain_terms + [v for v in load_vocabulary() if v.lower() not in seen]
    prompt = (", ".join(known_names) + ". " if known_names else "") \
        + DEFAULT_PROMPT + (" " + ", ".join(extra[:60]) + "." if extra else "")
    if packs:
        log("domain packs: " + ", ".join(p.stem for p in packs))
    # layout: CLI --user-channel > --mono > settings; anything but left/right = no user channel
    user_channel = (args.user_channel or ("none" if args.mono else None)
                    or dia.get("user_channel") or "none").lower()
    user_channel = user_channel if user_channel in ("left", "right") else None
    stereo = info["channels"] == 2 and user_channel is not None
    layout = (f"stereo (your mic on the {user_channel})" if stereo
              else ("mono" if info["channels"] == 1 else "stereo mix, no dedicated user channel"))
    log(f"{src.name}: {ts_short(info['duration'])}, {layout}; lang={lang}")

    with tempfile.TemporaryDirectory(prefix="meeting-") as td:
        wavs = split_channels(src, Path(td), user_channel if stereo else None)
        raw = {}
        for ch, wav in wavs.items():
            t0 = time.time()
            log(f"whisper {ch} …")
            raw[ch] = whisper_channel(wav, lang, model, prompt, task)
            log(f"whisper {ch}: {len(raw[ch]['segments'])} segments in {time.time() - t0:.0f}s")
        cleaned = {ch: clean_segments(r, info["duration"]) for ch, r in raw.items()}

        multi_ch = "right" if stereo else "mono"
        log("speaker embeddings + clustering …")
        t0 = time.time()
        embedder = Embedder()
        audio = load_wav(wavs[multi_ch])
        units, clusters = diarize_channel(cleaned[multi_ch], audio, embedder,
                                          num_speakers=args.num_speakers, threshold=threshold)
        log(f"diarized {multi_ch}: {len(units)} units, {len(clusters)} speakers in {time.time() - t0:.0f}s")
        units_by_channel = {multi_ch: units}
        left_centroid = None
        if stereo:
            lunits = [dict(s) for s in cleaned["left"]]
            units_by_channel["left"] = lunits
            laudio = load_wav(wavs["left"])
            embs = []
            for u in lunits:
                if u["end"] - u["start"] >= 1.5:
                    e = embedder.embed(laudio[int(u["start"] * SR):int(u["end"] * SR)])
                    if e is not None:
                        embs.append(e)
            if embs:
                left_centroid = np.mean(embs, axis=0)
                left_centroid /= (np.linalg.norm(left_centroid) + 1e-9)

    names = guess_names(clusters, attendees, meta["context"], auto_thr,
                        exclude={user_name} if stereo else None, display_floor=guess_floor)
    clusters, names, split_note = try_split_merged(
        units, clusters, names, orig_n=args.num_speakers, threshold=threshold,
        attendees=attendees, context=meta["context"], auto_thr=auto_thr,
        floor=guess_floor, exclude={user_name} if stereo else None)
    if split_note:
        log(split_note)
    doc = {
        "version": 2, "source": str(src), "created": datetime.now().isoformat(timespec="seconds"),
        "recorded_at": meta["recorded_at"], "context": meta["context"], "context_parts": meta["context_parts"],
        "attendees": attendees, "duration": round(info["duration"], 2), "stereo": stereo,
        "user_channel": user_channel if stereo else None,
        "language": lang, "task": task, "model": model, "embedding_model": ECAPA_MODEL,
        "diarization": {"threshold": threshold, "num_speakers": args.num_speakers,
                        "effective_num_speakers": len(clusters)},
    }
    assemble_doc(doc, units_by_channel, clusters, names, user_name)
    if stereo and left_centroid is not None:
        doc["speakers"][user_name]["centroid"] = emb_list(left_centroid)
        if user_name != USER_PLACEHOLDER:
            # the user channel is always you: keep your own profile fresh
            add_centroid(user_name, left_centroid, source=src.name, when=(meta["recorded_at"] or "")[:10] or None,
                         context=meta["context"], seconds=doc["speakers"][user_name]["seconds"])

    paths["json"].write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    paths["md"].write_text(render_markdown(doc), encoding="utf-8")
    write_review_yaml(doc, paths["yaml"])
    log(f"wrote {paths['md'].name}, {paths['json'].name}, {paths['yaml'].name}")
    print_review(doc, paths)


def print_review(doc: dict, paths: Optional[dict] = None) -> None:
    print("\n=== speakers ===")
    for key, v in doc["speakers"].items():
        if v.get("channel") == "left":
            print(f"{key} (own mic channel) — {v['seconds'] / 60:.1f} min")
            continue
        g = v.get("guess") or []
        gs = ", ".join(f"{r['name']} {r['score']:.2f}" + (" (weak)" if r.get("weak") else "")
                       + (f" (+{r['bonus']:.2f} {r['why']})" if r.get("bonus") else "")
                       for r in g[:3]) or "no match in store"
        nm = f" -> {v['name']}" + (" (auto)" if v.get("auto") else "") if v.get("name") else ""
        minor = "  [minor]" if v["seconds"] < 30 else ""
        print(f"{key}{nm} — {v['seconds'] / 60:.1f} min, {v['turns']} turns | guess: {gs}{minor}")
        if v.get("ambiguous"):
            print(f"    WARNING: {' and '.join(v['ambiguous'])} tie on this cluster — it may merge two speakers")
        first, longest = speaker_samples(doc, key)
        for t in (first[:2] + longest[:1]):
            print(f"    [{ts_short(t['start'])}] {t['text'][:160]}")
    missing = unmatched_attendees(doc)
    if missing:
        print(f"\nattendees not matched to any cluster: {', '.join(missing)}"
              " — an unidentified cluster above may be them")
    yaml_path = (paths or out_paths(Path(doc["source"])))["yaml"]
    print(f"\nReview sheet: {yaml_path}")


def load_doc(path_arg: str) -> tuple[dict, dict]:
    p = Path(path_arg).expanduser().resolve()
    paths = out_paths(p)
    if not paths["json"].exists():
        sys.exit(f"no transcript json for {p.name} — run `meeting.py run` first")
    return json.loads(paths["json"].read_text(encoding="utf-8")), paths


def cmd_rediarize(args) -> None:
    """Re-cluster the multi-speaker channel from stored unit embeddings (no Whisper rerun)."""
    settings = load_settings()
    doc, paths = load_doc(args.audio)
    dia = settings.get("diarization", {})
    threshold = args.threshold if args.threshold is not None else doc["diarization"].get("threshold", 0.55)
    auto_thr = float(dia.get("auto_label_threshold", 0.70))
    attendees = [a.strip() for a in (args.attendees or "").split(",") if a.strip()] or doc.get("attendees", [])
    multi_ch = "right" if doc.get("stereo") else "mono"
    units = [dict(s) for s in doc["segments"] if s["channel"] == multi_ch]
    for u in units:
        u["emb"] = np.asarray(u["emb"]) if u.get("emb") is not None else None
        u.pop("cluster", None)

    units_sorted = sorted(units, key=lambda u: u["start"])
    if not any(u["emb"] is not None for u in units_sorted):
        sys.exit("no embeddings stored; run with --force instead")
    clusters = cluster_units(units_sorted, num_speakers=args.num_speakers, threshold=threshold)

    user_name = next((k for k, v in doc["speakers"].items() if v.get("channel") == "left"), None)
    guess_floor = float(dia.get("guess_display_threshold", 0.35))
    names = guess_names(clusters, attendees, doc.get("context", ""), auto_thr,
                        exclude={user_name} if user_name else None,
                        display_floor=guess_floor)
    clusters, names, split_note = try_split_merged(
        units_sorted, clusters, names, orig_n=args.num_speakers, threshold=threshold,
        attendees=attendees, context=doc.get("context", ""), auto_thr=auto_thr,
        floor=guess_floor, exclude={user_name} if user_name else None)
    if split_note:
        log(split_note)
    # carry manually confirmed names over to the re-clustered speakers (by centroid match)
    for key, old in doc["speakers"].items():
        if old.get("channel") == "left" or not old.get("name") or old.get("auto") or old.get("centroid") is None:
            continue
        oc = np.asarray(old["centroid"])
        best = max((cid for cid in clusters if clusters[cid]["centroid"] is not None),
                   key=lambda cid: cosine(oc, clusters[cid]["centroid"]), default=None)
        if best is not None and cosine(oc, clusters[best]["centroid"]) >= 0.85:
            names[best]["name"] = old["name"]
            names[best]["auto"] = False
    left_units = [s for s in doc["segments"] if s["channel"] == "left"]
    left_info = doc["speakers"].get(user_name) if user_name else None
    ub = {multi_ch: units_sorted}
    if left_units:
        ub["left"] = left_units
    doc["diarization"] = {"threshold": threshold, "num_speakers": args.num_speakers,
                          "effective_num_speakers": len(clusters)}
    doc["attendees"] = attendees
    assemble_doc(doc, ub, clusters, names, user_name or USER_PLACEHOLDER)
    if left_info and user_name:
        doc["speakers"][user_name]["centroid"] = left_info.get("centroid")
    paths["json"].write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    paths["md"].write_text(render_markdown(doc), encoding="utf-8")
    write_review_yaml(doc, paths["yaml"])
    log(f"re-diarized: {len(clusters)} speakers (threshold {threshold}, n={args.num_speakers})")
    print_review(doc, paths)


def parse_mapping(s: Optional[str]) -> dict[str, str]:
    out = {}
    if not s:
        return out
    for part in re.split(r"[,;\n]", s):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def cmd_rename(args) -> None:
    doc, paths = load_doc(args.audio)
    mapping = read_review_yaml(paths["yaml"])
    mapping.update(parse_mapping(args.mapping))
    changed = []
    for key, v in doc["speakers"].items():
        if v.get("channel") == "left":
            continue
        new = mapping.get(key, "")
        if new == "-":  # explicit "clear this name"
            v["name"] = None
            v["auto"] = False
            continue
        if not new or new == key or re.fullmatch(r"speaker \d+", new.lower()):
            continue
        if v.get("name") != new or v.get("auto"):
            changed.append((key, new))
        v["name"] = new
        v["auto"] = False
    # also allow renaming the user-channel label
    for key, v in list(doc["speakers"].items()):
        if v.get("channel") == "left" and mapping.get(key) and mapping[key] != key:
            v["name"] = mapping[key]
            # the user channel belongs to the recording user: learn their name once
            if (v["name"] != USER_PLACEHOLDER
                    and not load_settings().get("diarization", {}).get("user_name")):
                update_setting("diarization", "user_name", v["name"])
                log(f"learned your name: diarization.user_name = {v['name']} (settings.yaml)")
    paths["json"].write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    paths["md"].write_text(render_markdown(doc), encoding="utf-8")
    write_review_yaml(doc, paths["yaml"])
    src = Path(doc["source"])
    enrolled = []
    if not args.no_enrol:
        # several clusters can carry the same name (main voice + fragment clusters);
        # enrol only the largest one — add_centroid replaces per source, so enrolling
        # them all would leave whichever came last (possibly a fragment) as the print.
        # The user channel takes part too, so naming a placeholder "You" enrols you.
        by_name: dict[str, dict] = {}
        for v in doc["speakers"].values():
            if not v.get("name") or v["name"] == USER_PLACEHOLDER or v.get("centroid") is None:
                continue
            cur = by_name.get(v["name"])
            if cur is None or v["seconds"] > cur["seconds"]:
                by_name[v["name"]] = v
        for name, v in by_name.items():
            if v["seconds"] < 8:
                continue  # too little speech even for a weak voiceprint
            weak = v["seconds"] < 20
            add_centroid(name, np.asarray(v["centroid"]), source=src.name,
                         when=(doc.get("recorded_at") or "")[:10] or None,
                         context=doc.get("context", ""), seconds=v["seconds"], weak=weak)
            enrolled.append(name + (" (weak)" if weak else ""))
    named = {k: v.get("name") for k, v in doc["speakers"].items() if v.get("name")}
    log("names: " + ", ".join(f"{k} -> {n}" for k, n in named.items()))
    if enrolled:
        log("enrolled/updated profiles: " + ", ".join(sorted(set(enrolled))))
    log(f"updated {paths['md'].name}, {paths['yaml'].name}, {paths['json'].name}")


def parse_list(s: Optional[str]) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def cmd_normalize(args) -> None:
    """Rewrite domain terms Whisper misheard, then re-render the markdown.

    Deliberately confidence-blind: the worst offenders are the ones Whisper is
    *sure* about, because condition_on_previous_text carries an early mistake
    forward and the model's confidence climbs with each repeat.
    """
    doc, paths = load_doc(args.audio)
    tokens = set(doc.get("context_tokens") or [])
    if not tokens:
        tokens = set(parse_filename(Path(doc["source"])).get("context_tokens") or [])
    packs = resolve_packs(tokens, parse_list(args.domain))
    terms = load_domain(packs)
    if not terms:
        sys.exit(f"no domain terms matched — add a pack under {DOMAIN_DIR}")
    print("domain packs: " + ", ".join(p.stem for p in packs) + "\n")

    fuzzy = args.fuzzy if args.fuzzy is not None else DEFAULT_FUZZY
    tally: dict[tuple[str, str], int] = {}
    first_at: dict[tuple[str, str], float] = {}
    n_seg = 0

    for seg in doc["segments"]:
        new_text, changes = normalize_text(seg.get("text", ""), terms, fuzzy)
        if changes:
            seg["text"] = new_text
            n_seg += 1
            for pair in changes:
                tally[pair] = tally.get(pair, 0) + 1
                first_at.setdefault(pair, seg.get("start", 0.0))
        # keep the word-level track consistent with the text it came from
        for w in seg.get("words") or []:
            new_w, ch = normalize_text(w.get("w", ""), terms, fuzzy)
            if ch:
                w["w"] = new_w

    if not tally:
        print("nothing to change — no domain terms matched")
        return

    width = max(len(o) for o, _ in tally) + 2
    print(f"{'was':<{width}}{'→ becomes':<26}{'n':>4}   first at")
    print("-" * (width + 44))
    for (old, new), n in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0][0].lower())):
        print(f"{old:<{width}}{new:<26}{n:>4}   {ts(first_at[(old, new)])}")
    total = sum(tally.values())
    print(f"\n{total} replacement(s) across {n_seg} segment(s), "
          f"{len(tally)} distinct form(s); fuzzy≥{fuzzy}")

    if not args.apply:
        print("\ndry run — nothing written. Re-run with --apply to save.")
        return

    doc["normalized"] = {"fuzzy": fuzzy, "replacements": total,
                         "packs": [p.stem for p in packs]}
    paths["json"].write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    paths["md"].write_text(render_markdown(doc), encoding="utf-8")
    log(f"updated {paths['md'].name}, {paths['json'].name}")


def cmd_speakers(args) -> None:
    if args.action == "forget":
        ok = delete_profile(args.name)
        print(("deleted " if ok else "no profile named ") + args.name)
        return
    profs = list_profiles()
    if not profs:
        print("no speaker profiles yet")
        return
    for p in profs:
        secs = sum(c.get("seconds", 0) for c in p["centroids"])
        dates = sorted(c.get("date", "") for c in p["centroids"])
        print(f"{p['name']}: {len(p['centroids'])} sessions, {secs / 60:.0f} min, {dates[0]}..{dates[-1]}")
        for c in p.get("contexts", [])[:6]:
            print(f"    - {c}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="transcribe + diarize a recording")
    r.add_argument("audio")
    r.add_argument("-l", "--language", help="ISO code or 'auto' (default from settings)")
    r.add_argument("-n", "--num-speakers", type=int, help="number of speakers on the right/mono channel")
    r.add_argument("-a", "--attendees", help="comma-separated names likely present (biases matching)")
    r.add_argument("-t", "--threshold", type=float, help="clustering cosine-distance threshold")
    r.add_argument("-u", "--user-channel", choices=["left", "right", "none"],
                   help="physical channel carrying your own mic (default: settings "
                        "diarization.user_channel; 'none' = single multi-speaker mix)")
    r.add_argument("--mono", action="store_true", help="alias for --user-channel none")
    r.add_argument("--task", choices=["transcribe", "translate"], default="transcribe",
                   help="Whisper task: 'translate' renders all speech as English (for mixed-language meetings; pair with -l <source language>)")
    r.add_argument("--domain", help="comma-separated domain pack names, overriding filename detection")
    r.add_argument("--force", action="store_true")
    r.set_defaults(func=cmd_run)

    d = sub.add_parser("rediarize", help="re-cluster from stored embeddings (no Whisper rerun)")
    d.add_argument("audio")
    d.add_argument("-n", "--num-speakers", type=int)
    d.add_argument("-a", "--attendees")
    d.add_argument("-t", "--threshold", type=float)
    d.set_defaults(func=cmd_rediarize)

    n = sub.add_parser("rename", help="apply speaker names from the yaml and/or a mapping; enrol profiles")
    n.add_argument("audio")
    n.add_argument("mapping", nargs="?", help='"Speaker 1=Name, Speaker 2=Other"')
    n.add_argument("--no-enrol", action="store_true")
    n.set_defaults(func=cmd_rename)

    z = sub.add_parser("normalize", help="fix domain terms Whisper misheard; re-render the markdown")
    z.add_argument("audio")
    z.add_argument("--apply", action="store_true", help="write the changes (default: preview only)")
    z.add_argument("--fuzzy", type=float, help=f"near-miss threshold 0-1 (default {DEFAULT_FUZZY})")
    z.add_argument("--domain", help="comma-separated pack names, overriding filename detection")
    z.set_defaults(func=cmd_normalize)

    s = sub.add_parser("speakers", help="list / forget stored speaker profiles")
    s.add_argument("action", nargs="?", default="list", choices=["list", "forget"])
    s.add_argument("name", nargs="?")
    s.set_defaults(func=cmd_speakers)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
