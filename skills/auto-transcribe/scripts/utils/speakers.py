"""Speaker profile management using voice embeddings.

v2 profile format (ECAPA, one centroid per session):

    {
      "name": "Alex Example",
      "model": "speechbrain/spkrec-ecapa-voxceleb",
      "centroids": [
        {"embedding": [...192 floats...], "source": "<file name>", "date": "2026-05-20",
         "context": "Tekoälyn hyödyntäminen presentaatioissa", "seconds": 1234.5}
      ],
      "contexts": ["tekoälyn hyödyntäminen presentaatioissa", ...],
      "updated": "2026-08-19"
    }

A centroid may carry "weak": true — built from little speech (8–20 s). Weak
centroids take part in matching (so quiet attendees still get guessed) but a
match whose best centroid is weak is flagged and never auto-applied.

Legacy v1 profiles (single "embedding" key, resemblyzer) are still loadable but are
ignored for matching when their model differs from the requested one.
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import Optional

import numpy as np

from .config import SPEAKERS_DIR, ensure_dirs

ECAPA_MODEL = "speechbrain/spkrec-ecapa-voxceleb"
MAX_CENTROIDS_PER_PROFILE = 24

CONTEXT_STOPWORDS = {
    "meeting", "daily", "weekly", "monthly", "sync", "sisäinen", "sisainen",
    "internal", "project", "projekti", "dev", "demo", "review", "session", "call",
    "palaveri", "kokous", "ja", "and", "the", "of", "for", "with", "-", "–",
}


def slugify(name: str) -> str:
    safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in name)
    return safe.strip().replace(" ", "_").lower()


def context_tokens(text: str) -> set[str]:
    """Bag of words for a recording's context (the filename remainder)."""
    toks = re.split(r"[^0-9a-zA-ZäöåÄÖÅ]+", text.lower())
    return {t for t in toks if t and t not in CONTEXT_STOPWORDS and len(t) > 1}


def context_parts(text: str) -> list[str]:
    """'CustomerX - ProjectY - dev daily' -> ['customerx', 'projecty', 'dev daily'] (lowercased, trimmed)."""
    return [p.strip().lower() for p in re.split(r"\s[-–]\s", text or "") if p.strip()]


def context_bonus(recording_context: str, profile_contexts: list[str]) -> tuple[float, str]:
    """Hierarchical context bias between a recording and the contexts a profile was seen in.

    Uses the ' - ' segments of the filename context:
      same organisation/entity (1st segment)   +0.05
      same project (2nd segment), on top        +0.04
      same full context, on top                 +0.03
    Falls back to token-Jaccard (0..0.05) for loosely named files without segments.
    Returns (bonus, reason) with the best-scoring profile context.
    """
    rc = (recording_context or "").strip().lower()
    rparts = context_parts(rc)
    rtok = context_tokens(rc)
    best, reason = 0.0, ""
    for pc in profile_contexts or []:
        pc = (pc or "").strip().lower()
        pparts = context_parts(pc)
        b, why = 0.0, []
        if rparts and pparts and rparts[0] == pparts[0]:
            b += 0.05
            why.append("org")
            if len(rparts) > 1 and len(pparts) > 1 and rparts[1] == pparts[1]:
                b += 0.04
                why.append("project")
                if rc == pc:
                    b += 0.03
                    why.append("same context")
        else:
            ptok = context_tokens(pc)
            if rtok and ptok:
                j = len(rtok & ptok) / len(rtok | ptok)
                if j > 0:
                    b += 0.05 * j
                    why.append(f"words {j:.0%}")
        if b > best:
            best, reason = b, "same " + "/".join(why) if why and why[0] in ("org",) else ", ".join(why)
    return round(best, 3), reason


def _profile_path(name: str) -> Path:
    return SPEAKERS_DIR / f"{slugify(name)}.json"


def load_profile(name: str) -> Optional[dict]:
    p = _profile_path(name)
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def list_profiles(model: Optional[str] = ECAPA_MODEL) -> list[dict]:
    """All profiles (v2 only when `model` is given; pass None to include legacy)."""
    ensure_dirs()
    out = []
    for p in sorted(SPEAKERS_DIR.glob("*.json")):
        try:
            with open(p) as f:
                d = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        if "centroids" not in d:
            if model is None:
                out.append({"name": d.get("name", p.stem), "path": str(p), "legacy": True,
                            "centroids": [], "contexts": []})
            continue
        if model and d.get("model") != model:
            continue
        d["path"] = str(p)
        out.append(d)
    return out


def add_centroid(
    name: str,
    embedding: np.ndarray,
    *,
    source: str,
    when: Optional[str] = None,
    context: str = "",
    seconds: float = 0.0,
    model: str = ECAPA_MODEL,
    weak: bool = False,
) -> Path:
    """Append a session centroid to a speaker profile (creating it if needed).

    Re-running on the same source replaces that source's centroid instead of
    duplicating it. Keeps at most MAX_CENTROIDS_PER_PROFILE (newest win).
    `weak` marks a centroid built from little speech: it still matches, but the
    match is flagged and never auto-applied.
    """
    ensure_dirs()
    emb = np.asarray(embedding, dtype=float)
    emb = emb / (np.linalg.norm(emb) + 1e-9)
    prof = load_profile(name)
    if prof is None or "centroids" not in prof or prof.get("model") != model:
        prof = {"name": name, "model": model, "centroids": [], "contexts": []}
    prof["centroids"] = [c for c in prof["centroids"] if c.get("source") != source]
    entry = {
        "embedding": [round(float(x), 5) for x in emb],
        "source": source,
        "date": when or date.today().isoformat(),
        "context": context,
        "seconds": round(float(seconds), 1),
    }
    if weak:
        entry["weak"] = True
    prof["centroids"].append(entry)
    prof["centroids"] = prof["centroids"][-MAX_CENTROIDS_PER_PROFILE:]
    ctx = context.strip().lower()
    if ctx and ctx not in prof["contexts"]:
        prof["contexts"].append(ctx)
    prof["updated"] = date.today().isoformat()
    path = _profile_path(name)
    with open(path, "w") as f:
        json.dump(prof, f, ensure_ascii=False, indent=1)
    return path


def delete_profile(name: str) -> bool:
    p = _profile_path(name)
    if p.exists():
        p.unlink()
        return True
    return False


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9))


def match_embedding(
    embedding: np.ndarray,
    *,
    attendees: Optional[list[str]] = None,
    context: str = "",
    model: str = ECAPA_MODEL,
    top_k: int = 3,
) -> list[dict]:
    """Rank stored profiles against an embedding.

    Returns up to top_k dicts: {name, score (raw best cosine), adjusted, bonus, weak}.
    `adjusted` = raw + bonus, where bonus rewards attendee hints and context overlap.
    `weak` is True when the best-matching centroid was built from little speech.
    """
    attendees_l = {a.strip().lower() for a in (attendees or []) if a.strip()}
    ranked = []
    for prof in list_profiles(model):
        if not prof["centroids"]:
            continue
        sims = [(cosine(embedding, np.asarray(c["embedding"])), bool(c.get("weak")))
                for c in prof["centroids"]]
        raw, best_weak = max(sims, key=lambda t: t[0])
        bonus, reasons = 0.0, []
        if prof["name"].lower() in attendees_l or any(
            a and (a in prof["name"].lower()) for a in attendees_l
        ):
            bonus += 0.08
            reasons.append("attendee")
        cb, why = context_bonus(context, prof.get("contexts", []))
        if cb > 0:
            bonus += cb
            reasons.append(why)
        ranked.append({"name": prof["name"], "score": raw, "adjusted": raw + bonus,
                       "bonus": round(bonus, 3), "why": ", ".join(r for r in reasons if r),
                       "sessions": len(prof["centroids"]), "weak": best_weak})
    ranked.sort(key=lambda r: r["adjusted"], reverse=True)
    return ranked[:top_k]


# ---- legacy v1 API kept for diarize.py -------------------------------------

def save_speaker_profile(name: str, embedding: np.ndarray, metadata: dict = None) -> Path:
    ensure_dirs()
    profile = {"name": name, "embedding": embedding.tolist(), "metadata": metadata or {}}
    path = _profile_path(name)
    with open(path, "w") as f:
        json.dump(profile, f, indent=2)
    return path


def load_speaker_profile(name_or_path: str) -> Optional[dict]:
    path = Path(name_or_path)
    if not path.exists():
        path = _profile_path(name_or_path)
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    if "embedding" in data:
        data["embedding"] = np.array(data["embedding"])
    return data


def list_speaker_profiles() -> list[dict]:
    return [{"name": p["name"], "path": p["path"], "metadata": p.get("metadata", {})}
            for p in list_profiles(model=None)]


def delete_speaker_profile(name: str) -> bool:
    return delete_profile(name)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return cosine(a, b)


def match_speaker(embedding: np.ndarray, threshold: float = 0.75) -> Optional[tuple[str, float]]:
    best = None
    for info in list_speaker_profiles():
        prof = load_speaker_profile(info["path"])
        if prof is None or "embedding" not in prof:
            continue
        s = cosine(embedding, prof["embedding"])
        if s > threshold and (best is None or s > best[1]):
            best = (prof["name"], s)
    return best
