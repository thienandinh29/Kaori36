"""Step V2b: pronunciation, grammar and vocabulary queues in the reviewer portal."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.api import review_portal as routes
from app.config import REPO_ROOT
from app.services.review_portal import (
    ReviewPortal,
    Sources,
    create_batch,
    issue_token,
    shuffled,
    speech_targets,
    vocab_id,
)
from app.validation.sampling import everything, random_sample
from app.validation.store import add_reviewer, effective_tier
from app.vocabulary.wordlist import shared_wordlist

NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
VOCAB = REPO_ROOT / "data" / "vocabulary" / "core-seed.yaml"
VOCAB_SA = REPO_ROOT / "data-sa" / "vocabulary"
PRON = REPO_ROOT / "data" / "pronunciation"
ANALYSIS: dict[str, Any] = {
    "recognised": [],
    "targets": [
        {"sound": "th-voiceless", "word": "think", "phone": "θ", "gop": -1.0,
         "competitor": "t", "start_ms": 100, "end_ms": 180},
        {"sound": "final-t", "word": "best", "phone": "t", "gop": -0.2,
         "competitor": None, "start_ms": 600, "end_ms": 650},
    ],
}  # fmt: skip


@pytest.fixture
def env(database_url: str, tmp_path: Path) -> Iterator[dict[str, Any]]:
    items = tmp_path / "items.yaml"
    items.write_text(
        yaml.safe_dump(
            {
                "course": "english-ielts",
                "items": [
                    {
                        "id": "g1",
                        "node": "be-present",
                        "status": "draft",
                        "prompt": "My sister ___ a nurse.",
                        "options": [
                            {"text": "is", "correct": True},
                            {"text": "are"},
                            {"text": "am"},
                            {"text": "be"},
                        ],
                    },
                ],
            }
        ),
        "utf-8",
    )
    pool = ConnectionPool(database_url, open=True)
    with pool.connection() as conn:
        owner = conn.execute(
            "insert into learners(display_name) values ('Owner') returning id::text"
        ).fetchone()
        other = conn.execute(
            "insert into learners(display_name) values ('Other') returning id::text"
        ).fetchone()
        assert owner is not None and other is not None

        def rec(learner: str, keep: bool) -> str:
            row = conn.execute(
                "insert into speech_recordings(learner_id,prompt_id,consent,keep,audio,seconds,"
                "quality,status,analysis) values (%s,'p11','voice-v1',%s,'\\x52494646',1,'{}',"
                "'analysed',%s) returning id::text",
                (learner, keep, Jsonb(ANALYSIS)),
            ).fetchone()
            assert row is not None
            return str(row[0])

        kept = rec(owner[0], True)
        rec(owner[0], False)  # not kept: never sent
        rec(other[0], True)  # not an owner: never sent
        owners = {owner[0]}
        targets = speech_targets(conn, owner[0], owners)
        with pytest.raises(ValueError):
            speech_targets(conn, other[0], owners)
        phon = add_reviewer(conn, "P", "phonetics_expert", "", NOW)
        teacher = add_reviewer(conn, "T", "expert_teacher", "", NOW)
        tokens = {"phon": issue_token(conn, phon), "teacher": issue_token(conn, teacher)}
        speech = create_batch(conn, "Âm", "speech_target", everything(targets, 1), 1)
        with pytest.raises(ValueError):
            create_batch(conn, "x", "grammar_item", everything(["g1"], 1), 1, "ielts_rater")
        grammar = create_batch(conn, "Ngữ pháp", "grammar_item", everything(["g1"], 1), 1)
        words = shared_wordlist(VOCAB, VOCAB_SA).words
        vocab = create_batch(
            conn, "Từ", "vocab_entry", random_sample([vocab_id(w) for w in words], 3, 1), 1
        )
    app = FastAPI()
    sources = Sources(items=items, vocab=VOCAB, vocab_imported=VOCAB_SA, pronunciation=PRON)
    app.include_router(
        routes.create_router(ReviewPortal(lambda: pool, tmp_path, lambda: NOW, sources))
    )
    yield {"client": TestClient(app), "pool": pool, "tokens": tokens, "kept": kept,
           "targets": targets, "speech": speech, "grammar": grammar, "vocab": vocab}  # fmt: skip
    with pool.connection() as conn:
        for table in ("labels", "review_batches", "reviewers", "speech_recordings"):
            conn.execute(f"delete from {table}")
    pool.close()


def h(token: str) -> dict[str, str]:
    return {"X-Reviewer-Token": token}


def test_only_kept_owner_recordings_reach_a_reviewer(env: dict[str, Any]) -> None:
    assert env["targets"] == [f"{env['kept']}:0", f"{env['kept']}:1"]
    c, tok = env["client"], h(env["tokens"]["phon"])
    url = f"/review/batches/{env['speech']}"
    item = c.get(f"{url}/next", headers=tok).json()["item"]
    index = int(item["content_id"].rsplit(":", 1)[1])
    target = ANALYSIS["targets"][index]
    sounds = {"th-voiceless": ("θ", "Âm /θ/ (think, three)"),
              "final-t": ("t", "Âm /t/ cuối từ (cat, start)")}  # fmt: skip
    assert item == {
        "content_id": f"{env['kept']}:{index}",
        "content_type": "speech_target",
        "sentence": "I think the best part of the test was the last question.",
        "word": target["word"],
        "ipa": sounds[target["sound"]][0],
        "sound_vi": sounds[target["sound"]][1],
        "start_ms": target["start_ms"],
        "end_ms": target["end_ms"],
    }
    audio = c.get(f"{url}/items/{item['content_id']}/audio", headers=tok)
    assert audio.status_code == 200 and audio.content == b"RIFF"
    assert audio.headers["content-type"] == "audio/wav"
    # A teacher's token cannot reach a phonetics batch or its audio.
    teacher = h(env["tokens"]["teacher"])
    assert c.get(f"{url}/items/{item['content_id']}/audio", headers=teacher).status_code == 404
    # Labels are Gold; a sound takes no reason.
    post = f"{url}/items/{item['content_id']}"
    bad = c.post(post, headers=tok, json={"verdict": "wrong", "reason": "definition"})
    assert bad.status_code == 422
    assert c.post(post, headers=tok, json={"verdict": "wrong"}).status_code == 200
    with env["pool"].connection() as conn:
        e = effective_tier(conn, "speech_target", item["content_id"], "phone_ok")
        assert (e.tier, e.value) == ("gold", "wrong")
        # Once the recording is no longer kept, it is no longer served.
        conn.execute("update speech_recordings set keep=false where id::text=%s", (env["kept"],))
    left = c.get(f"{url}/next", headers=tok).json()
    assert left["item"] is None and left["unavailable"] == 1
    gone = c.get(f"{url}/items/{item['content_id']}/audio", headers=tok)
    assert gone.status_code == 404


def test_grammar_items_are_shuffled_and_keyed(env: dict[str, Any]) -> None:
    c, tok = env["client"], h(env["tokens"]["teacher"])
    url = f"/review/batches/{env['grammar']}"
    item = c.get(f"{url}/next", headers=tok).json()["item"]
    order = shuffled("g1", 4)
    assert item["options"] == [["is", "are", "am", "be"][i] for i in order]
    assert item["options"][item["key"]] == "is"
    assert "correct" not in str(item) and "misconception" not in str(item)
    post = f"{url}/items/g1"
    assert c.post(post, headers=tok, json={"verdict": "wrong"}).status_code == 422
    assert (
        c.post(post, headers=tok, json={"verdict": "wrong", "reason": "gloss"}).status_code == 422
    )
    ok = c.post(post, headers=tok, json={"answer": "is", "verdict": "right"})
    assert ok.status_code == 200


def test_vocabulary_entries(env: dict[str, Any]) -> None:
    c, tok = env["client"], h(env["tokens"]["teacher"])
    url = f"/review/batches/{env['vocab']}"
    item = c.get(f"{url}/next", headers=tok).json()["item"]
    assert item["content_type"] == "vocab_entry" and item["definition"] and item["examples"]
    assert all("___" not in s for s in item["forms"])
    post = f"{url}/items/{item['content_id']}"
    ok = c.post(post, headers=tok, json={"verdict": "wrong", "reason": "gloss", "note": "sai"})
    assert ok.status_code == 200
    assert c.get(f"{url}/next", headers=tok).json()["done"] == 1


def test_vocab_ids_are_unique_and_url_safe() -> None:
    ids = [vocab_id(w) for w in shared_wordlist(VOCAB, VOCAB_SA).words]
    assert all(i and all(ch.isalnum() or ch == "-" for ch in i) for i in ids)
    assert len(set(ids)) == len(ids)
