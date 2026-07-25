from __future__ import annotations

import random
from collections import defaultdict
from datetime import UTC, datetime

from ..repositories.questions import list_questions


def progress_state(question: dict[str, object]) -> str:
    shown, correct, wrong = int(question["shown_count"]), int(question["correct_count"]), int(question["wrong_count"])
    if not shown: return "new"
    if wrong >= 2 and wrong >= correct: return "problematic"
    if shown >= 3 and correct / shown >= 0.8 and wrong <= 1: return "mastered"
    return "learning"


def _weight(question: dict[str, object], now: datetime) -> float:
    shown, correct, wrong = int(question["shown_count"]), int(question["correct_count"]), int(question["wrong_count"])
    last = question.get("last_shown_at")
    days = 30.0 if not last else min(30.0, max(0.0, (now - datetime.fromisoformat(str(last))).total_seconds() / 86400))
    return 4 + wrong * 5 + (0 if shown else 6) + days / 7 + int(question["difficulty"]) - correct * 1.5


def select_questions(mode: str, count: int, video_ids: list[str] | None = None, seed: int | None = None, include_mastered: bool = True) -> list[dict[str, object]]:
    if count < 1: raise ValueError("Cantidad debe ser positiva")
    items = list_questions(video_ids)
    if not include_mastered: items = [item for item in items if progress_state(item) != "mastered"]
    if not items: return []
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    count = min(count, len(items))
    if mode == "balanced" or mode == "exam":
        groups: dict[str, list[dict[str, object]]] = defaultdict(list)
        for item in items: groups[str(item["topic"])].append(item)
        selected: list[dict[str, object]] = []
        while groups and len(selected) < count:
            for topic in list(groups):
                if len(selected) == count: break
                selected.append(groups[topic].pop(rng.randrange(len(groups[topic]))))
                if not groups[topic]: del groups[topic]
        return selected
    if mode == "new":
        fresh = [item for item in items if not int(item["shown_count"])]
        pool = fresh or items; return list(rng.sample(pool, min(count, len(pool))))
    if mode == "wrong_review":
        failed = [item for item in items if int(item["wrong_count"])]
        pool = failed or items; return list(rng.sample(pool, min(count, len(pool))))
    if mode == "smart":
        remaining = items[:]; selected = []
        while remaining and len(selected) < count:
            weights = [_weight(item, datetime.now(UTC)) for item in remaining]
            chosen = rng.choices(remaining, weights=weights, k=1)[0]; selected.append(chosen); remaining.remove(chosen)
        return selected
    return list(rng.sample(items, count))


def shuffle_options(question: dict[str, object], seed: int | None = None) -> dict[str, object]:
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    presentation = dict(question); options = list(question["options"]); rng.shuffle(options); presentation["options"] = options
    return presentation
