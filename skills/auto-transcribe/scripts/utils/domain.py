"""Domain-vocabulary normalisation for transcripts.

Whisper mishears domain names in two distinct ways, and they need different
treatment:

  * **low-confidence one-offs** — the first time a name appears the model is
    unsure and guesses (``Verteks`` p=0.33, ``Verteiler`` p=0.47).
  * **confidently-wrong repeats** — ``condition_on_previous_text`` feeds that
    early guess forward, so the model grows *sure* of its own mistake
    (``Verteks`` p=0.99 later in the same recording).

A confidence gate only reaches the first kind. Matching here is therefore
deterministic and confidence-blind: a token is rewritten because it looks like
a known term, not because Whisper was unsure about it.

Finnish inflection is preserved by matching the *stem* and re-attaching
whatever followed it, so ``Verteksin`` becomes ``Vertexin`` rather than
``Vertex``. Where a stem swap would produce bad Finnish (vowel harmony:
``räpintöjä`` → *``rajapintöjä``), use an explicit ``map:`` entry instead.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import yaml

CONFIG_DIR = Path.home() / ".auto-transcribe" / "config"
DOMAIN_DIR = CONFIG_DIR / "domain"
LEGACY_DOMAIN_FILE = CONFIG_DIR / "domain.yaml"
SHARED_PACK = "_shared"

# Back-compat alias: older docs/callers referred to a single flat file.
DOMAIN_FILE = DOMAIN_DIR

# Letters that can occur inside a word we might rewrite (Finnish + common
# European diacritics), plus internal hyphen/apostrophe.
_L = r"0-9A-Za-zÄÖÅäöåÜüÉéÈèÀàÂâÇçÔôÛû"
WORD_RE = re.compile(rf"[{_L}]+(?:['’-][{_L}]+)*")

# A stem match only counts if what follows looks like an inflection/compound
# tail rather than the start of an unrelated word.
MAX_SUFFIX = 12
MIN_FUZZY_STEM = 5
DEFAULT_FUZZY = 0.82


@dataclass
class Term:
    canonical: str
    stems: list[str] = field(default_factory=list)      # lowercase, longest-first
    mapping: dict[str, str] = field(default_factory=dict)  # full token -> full replacement
    proper: bool = True      # keep canonical casing (names) vs follow source casing
    inflect: bool = True     # allow stem + preserved suffix
    fuzzy: bool = True       # allow near-miss matching against the stems


def available_packs() -> list[str]:
    """Pack names on disk, excluding the always-on shared one."""
    if not DOMAIN_DIR.is_dir():
        return []
    return sorted(p.stem for p in DOMAIN_DIR.glob("*.yaml")
                  if p.stem != SHARED_PACK and not p.stem.startswith("."))


def resolve_packs(context_tokens: Optional[set[str]] = None,
                  explicit: Optional[list[str]] = None) -> list[Path]:
    """Pick which term files to load.

    A pack applies when its filename appears in the recording's context tokens
    — the same signal that biases speaker matching, so "… Acme - CustomerX -
    ProjectY …" loads `customerx.yaml` and nothing from another customer. The
    shared pack always applies and is placed last, so a project term wins any
    conflict with it.
    """
    picked: list[Path] = []
    if explicit:
        for name in explicit:
            p = DOMAIN_DIR / f"{name.strip().lower()}.yaml"
            if p.exists():
                picked.append(p)
    elif context_tokens:
        for name in available_packs():
            if name.lower() in {t.lower() for t in context_tokens}:
                picked.append(DOMAIN_DIR / f"{name}.yaml")

    for extra in (DOMAIN_DIR / f"{SHARED_PACK}.yaml", LEGACY_DOMAIN_FILE):
        if extra.exists() and extra not in picked:
            picked.append(extra)
    return picked


def load_domain(paths: Optional[list[Path]] = None) -> list[Term]:
    """Load terms from the given files (shared-only when none are given).

    Order is significant: earlier files win, because `map` lookups take the
    first hit and equal-length stems keep the first match.
    """
    files = paths if paths is not None else resolve_packs()
    terms: list[Term] = []
    for f in files:
        terms.extend(_load_one(Path(f)))
    return terms


def _load_one(p: Path) -> list[Term]:
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    terms: list[Term] = []
    for raw in data.get("terms") or []:
        if not isinstance(raw, dict) or not raw.get("canonical"):
            continue
        canonical = str(raw["canonical"])
        stems = {str(v).lower() for v in (raw.get("variants") or [])}
        # the canonical spelling is always a valid stem, so correct tokens
        # match as no-ops instead of being fuzzy-matched onto something else
        stems.add(canonical.lower())
        mapping = {str(k).lower(): str(v) for k, v in (raw.get("map") or {}).items()}
        terms.append(Term(
            canonical=canonical,
            stems=sorted(stems, key=len, reverse=True),
            mapping=mapping,
            proper=bool(raw.get("proper", True)),
            inflect=bool(raw.get("inflect", True)),
            fuzzy=bool(raw.get("fuzzy", True)),
        ))
    return terms


def _plausible_suffix(s: str) -> bool:
    """An inflection tail, or a compound tail introduced by a dash.

    The dash form matters for tokens like "Verteks-tyyppinen", where the stem is
    misheard but the compound boundary after it is correct.
    """
    if s == "":
        return True
    body = s[1:] if s.startswith("-") else s
    return bool(body) and body.isalpha() and len(body) <= MAX_SUFFIX


def _match_case(base: str, source: str) -> str:
    if source.isupper() and len(source) > 1:
        return base.upper()
    if source[:1].isupper():
        return base[:1].upper() + base[1:]
    return base.lower()


def _build(term: Term, suffix: str, source: str) -> str:
    base = term.canonical if term.proper else _match_case(term.canonical, source)
    if not suffix:
        return base
    # the token carried its own compound dash — keep it verbatim
    if suffix.startswith("-"):
        return base + suffix
    # A multi-word canonical ("Sent to Supplier") takes the Finnish compound
    # dash — but only for a real ending. A stray letter or two reads better
    # glued on: "Sent to Supplierin", not "Sent to Supplier -in".
    if " " in base and len(suffix) >= 4:
        return f"{base} -{suffix}"
    return base + suffix


def _match(low: str, core: str, terms: list[Term],
           fuzzy: float, allow_fuzzy: bool = True) -> Optional[tuple[int, str]]:
    """Match one token, returning (chars consumed as stem, replacement)."""
    # A stem may never reach across a hyphen: in "Vertex-toimittaja" the dash
    # is a real compound boundary, and letting a fuzzy stem straddle it eats
    # the dash plus a letter ("Vertexoimittaja").
    bar = low.find("-")
    limit = bar if bar >= 0 else len(low)

    # 1. explicit full-token map — wins outright, used where a stem swap would
    #    produce bad Finnish
    for t in terms:
        if low in t.mapping:
            return len(low), t.mapping[low]

    # 2. exact stem prefix; longest stem across all terms wins
    best: Optional[tuple[int, str]] = None
    for t in terms:
        if not t.inflect:
            if low in t.stems and (best is None or len(low) > best[0]):
                best = (len(low), _build(t, "", core))
            continue
        for stem in t.stems:
            if "-" not in stem and len(stem) > limit:
                continue
            if low.startswith(stem) and _plausible_suffix(low[len(stem):]):
                if best is None or len(stem) > best[0]:
                    best = (len(stem), _build(t, core[len(stem):], core))
                break
    if best is not None:
        return best

    # 3. fuzzy head match, for near-misses not yet in the variant lists.
    #    Only for terms that opt in — a one-letter edit is enough to turn a
    #    correct word into a term ("fallback" scores 0.875 against "callback"),
    #    so anything whose canonical is an ordinary word sets fuzzy: false.
    scored: Optional[tuple[float, int, str]] = None
    for t in terms:
        if not (allow_fuzzy and t.fuzzy and t.inflect):
            continue
        for stem in t.stems:
            n = len(stem)
            if n < MIN_FUZZY_STEM or len(low) < n or not _plausible_suffix(low[n:]):
                continue
            if "-" not in stem and n > limit:
                continue
            score = SequenceMatcher(None, low[:n], stem).ratio()
            if score >= fuzzy and (scored is None or score > scored[0]):
                scored = (score, n, _build(t, core[n:], core))
    return (scored[1], scored[2]) if scored else None


def normalize_word(core: str, terms: list[Term], fuzzy: float = DEFAULT_FUZZY) -> Optional[str]:
    """Return the corrected spelling of one word, or None if it is left alone."""
    hit = _match(core.lower(), core, terms, fuzzy)

    # Whisper sprinkles spurious hyphens into names it is unsure of
    # ("ver-texin"). Retry without them — but only accept if the stem reaches
    # past the hyphen, so a legitimate Finnish compound keeps its dash:
    # "ver-texin" -> Vertexin, while "Vertex-tyyppiset" is left alone.
    if hit is None and "-" in core:
        cut = core.lower().find("-")
        flat = core.replace("-", "")
        # exact stems only — dropping the hyphen is already a guess, and
        # allowing a fuzzy match on top of it turns "Vertex-toimittaja" into
        # "Vertexoimittaja"
        alt = _match(flat.lower(), flat, terms, fuzzy, allow_fuzzy=False)
        if alt is not None and alt[0] > cut:
            hit = alt

    if hit is None or hit[1] == core:
        return None
    return hit[1]


def normalize_text(text: str, terms: list[Term],
                   fuzzy: float = DEFAULT_FUZZY) -> tuple[str, list[tuple[str, str]]]:
    """Rewrite every recognised term in `text`.

    Returns the new text and the (old, new) pairs that were changed.
    """
    if not text or not terms:
        return text, []
    changes: list[tuple[str, str]] = []
    out: list[str] = []
    pos = 0
    for m in WORD_RE.finditer(text):
        core = m.group(0)
        new = normalize_word(core, terms, fuzzy)
        if new is None:
            continue
        out.append(text[pos:m.start()])
        out.append(new)
        pos = m.end()
        changes.append((core, new))
    if not changes:
        return text, []
    out.append(text[pos:])
    return "".join(out), changes
