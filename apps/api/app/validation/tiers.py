"""Tiers of trust: Gold, Silver, Bronze (specs/validation/spec.md, step V1).

Pure functions. A label's own tier comes from its role, never from the caller. The effective tier of
one aspect of one item is computed from all its labels:

1. "unsure" values and learner feedback are ignored;
2. Gold when Gold labels exist and agree (disputed when they disagree);
3. Silver when at least two non-owner labels with different independence keys agree and no counted
   label disagrees; the owner's labels never count towards Silver, but a disagreement from the owner
   still marks the aspect disputed (anyone may raise a doubt; only agreement promotes);
4. Bronze for anything else (disputed when the labels conflict);
5. no tier without labels.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

Tier = Literal["gold", "silver", "bronze"]
OwnTier = Literal["gold", "bronze", "feedback"]
Role = Literal[
    "expert_teacher",
    "ielts_rater",
    "phonetics_expert",
    "dataset",
    "model",
    "source",
    "code_check",
    "owner_developer",
    "owner_learner",
]

EXPERT_ROLES: frozenset[str] = frozenset({"expert_teacher", "ielts_rater", "phonetics_expert"})
OWNER_ROLES: frozenset[str] = frozenset({"owner_developer", "owner_learner"})
ROLES: frozenset[str] = EXPERT_ROLES | OWNER_ROLES | {"dataset", "model", "source", "code_check"}
CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "reading_item",
        "grammar_item",
        "vocab_entry",
        "lesson",
        "speech_target",
        "essay",
        "text_level",
        "error_map",
        "competency_link",
    }
)
UNSURE = "unsure"


def own_tier(role: str) -> OwnTier:
    """The tier a single label carries by itself."""
    if role not in ROLES:
        raise ValueError(f"unknown role: {role}")
    if role in EXPERT_ROLES or role == "dataset":
        return "gold"
    if role == "owner_learner":
        return "feedback"
    return "bronze"


def model_family(model: str) -> str:
    """The maker of a model id.

    'baidu/ernie-5.5-flash-preview:free' -> 'baidu'; an id without a maker prefix uses its first
    word: 'deepseek-flash' -> 'deepseek'.
    """
    name = model.split(":", 1)[0].casefold()
    return name.split("/", 1)[0] if "/" in name else name.split("-", 1)[0]


def source_of(role: str, *, name: str = "", reviewer_id: str | None = None) -> tuple[str, str]:
    """(source, independence key) for a label, so callers cannot choose their own independence."""
    if role in EXPERT_ROLES:
        if not reviewer_id:
            raise ValueError("an expert label needs its reviewer")
        return f"reviewer:{reviewer_id}", f"reviewer:{reviewer_id}"
    if role in OWNER_ROLES:
        return "owner", "owner"
    if not name:
        raise ValueError(f"a {role} label needs a name")
    if role == "model":
        return f"model:{name}", f"model:{model_family(name)}"
    return f"{role}:{name}", f"{role}:{name}"


@dataclass(frozen=True)
class Label:
    role: str
    value: str
    independence: str


@dataclass(frozen=True)
class Effective:
    tier: Tier | None
    value: str | None  # None when disputed or unlabelled
    disputed: bool
    reason: str


def effective(labels: Iterable[Label]) -> Effective:
    counted = [x for x in labels if x.value != UNSURE and own_tier(x.role) != "feedback"]
    if not counted:
        return Effective(None, None, False, "no labels")

    gold = {x.value for x in counted if own_tier(x.role) == "gold"}
    if len(gold) == 1:
        return Effective("gold", next(iter(gold)), False, "expert labels agree")
    if gold:
        return Effective(None, None, True, "expert labels disagree")

    values = {x.value for x in counted}
    if len(values) > 1:
        # Anyone can raise a doubt, the owner included; only agreement promotes.
        return Effective("bronze", None, True, "the labels disagree")
    value = next(iter(values))
    keys = {x.independence for x in counted if x.role not in OWNER_ROLES}
    if len(keys) >= 2:
        return Effective("silver", value, False, f"{len(keys)} independent checks agree")
    return Effective("bronze", value, False, "one source only")
