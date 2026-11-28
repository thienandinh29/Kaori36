"""Step 5.6: SPK-001's feature rows, the manifest rules and the resumable extraction."""

import csv
import json
from pathlib import Path
from typing import Any

import pytest

from app.speaking.spk001 import extract, features, manifest
from app.speaking.spk001.__main__ import main
from app.speaking.transcribe import Refused, Unavailable
from tests.pronunciation.test_recordings import speech_like

MEASURES = {
    "words": 60,
    "recording_seconds": 40.0,
    "speaking_seconds": 30.0,
    "share_of_time": 0.5,
    "speech_rate": 120.0,
    "articulation_rate": 150.0,
    "pauses": {"per_minute": 6.0, "between_clauses": 4, "inside_clause": 2, "long": 1},
    "fillers": {"count": 3},
    "longest_run": {"words": 12, "seconds": 5.5},
}
LANGUAGE = {
    "skipped": None,
    "guard": {"template_words": 6, "repeated_words": 3},
    "vocabulary": {"mtld": 52.0, "beyond_b1_share": 0.12, "unknown_share": 0.03},
    "hints": [
        {"kind": "grammar"},
        {"kind": "grammar"},
        {"kind": "ending"},
    ],
}


def test_a_feature_row_is_made_only_of_the_stored_measures_and_checks() -> None:
    f = features.row(MEASURES, LANGUAGE)
    assert set(f) == set(features.FEATURES)
    assert f["speech_rate"] == 120.0 and f["pauses_per_minute"] == 6.0
    assert f["pauses_between_per_minute"] == 8.0 and f["pauses_inside_per_minute"] == 4.0
    assert f["long_pauses_per_minute"] == 2.0 and f["fillers_per_100_words"] == 5.0
    assert f["mtld"] == 52.0 and f["beyond_b1_share"] == 0.12
    # a missing ending is counted apart from grammar, per 100 words
    assert f["grammar_hints_per_100_words"] == 3.33 and f["endings_per_100_words"] == 1.67
    assert f["template_words_share"] == 0.1 and f["repeated_words_share"] == 0.05


def test_what_was_not_measured_is_none_not_zero() -> None:
    short = features.row(MEASURES, {"skipped": "short"})
    assert short["mtld"] is None and short["grammar_hints_per_100_words"] is None
    none = features.row(MEASURES, None)
    assert none["beyond_b1_share"] is None and none["template_words_share"] is None
    no_lt = features.row(MEASURES, {**LANGUAGE, "hints": None})  # LanguageTool not used
    assert no_lt["grammar_hints_per_100_words"] is None and no_lt["mtld"] == 52.0
    empty = features.row({"words": 0, "speaking_seconds": 0.0}, None)
    assert empty["speech_rate"] is None and empty["fillers_per_100_words"] is None
    assert empty["pauses_between_per_minute"] is None


def write_manifest(folder: Path, rows: list[dict[str, str]]) -> Path:
    cols = [
        "id", "audio", "speaker", "split", "test", "part", "score", "source", "question",
        "asked_seconds", "words",
    ]  # fmt: skip
    path = folder / "manifest.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    return path


def make(folder: Path, n: int = 3, **over: str) -> list[dict[str, str]]:
    rows = []
    for i in range(n):
        (folder / f"a{i}.wav").write_bytes(speech_like())
        rows.append(
            {
                "id": f"r{i}",
                "audio": f"a{i}.wav",
                "speaker": f"s{i}",
                "split": "train",
                "score": "3.5",
                "source": "own",
                **over,
            }
        )
    return rows


def test_a_good_manifest_loads_with_its_scores_untouched(tmp_path: Path) -> None:
    rows = make(tmp_path, asked_seconds="60", question="Do you live in a city?")
    items = manifest.load(write_manifest(tmp_path, rows))
    assert [i.id for i in items] == ["r0", "r1", "r2"]
    assert items[0].score == 3.5 and items[0].asked_seconds == 60.0 and items[0].words is None


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"id": "r0"}, "repeated"),
        ({"split": "test"}, "split must be one of"),
        ({"score": "high"}, "not a number"),
        ({"source": "web"}, "source must be"),
        ({"audio": "missing.wav"}, "audio file not found"),
        ({"id": ""}, "id is empty"),
    ],
)
def test_a_bad_row_is_refused_with_its_row_number(
    tmp_path: Path, change: dict[str, str], message: str
) -> None:
    rows = make(tmp_path)
    rows[1] = {**rows[1], **change}
    with pytest.raises(manifest.ManifestError, match=message) as exc:
        manifest.load(write_manifest(tmp_path, rows))
    assert "row" in str(exc.value) or "repeated" in message


def test_a_speaker_in_two_splits_is_refused(tmp_path: Path) -> None:
    rows = make(tmp_path)
    rows[1] = {**rows[1], "speaker": "s0", "split": "eval"}
    with pytest.raises(manifest.ManifestError, match="more than one split"):
        manifest.load(write_manifest(tmp_path, rows))


def test_corpus_rows_wait_for_the_owners_licence_note_and_output_stays_private(
    tmp_path: Path,
) -> None:
    private = tmp_path / "data" / "private"
    private.mkdir(parents=True)
    rows = make(tmp_path, source="corpus")
    items = manifest.load(write_manifest(tmp_path, rows))
    out = private / "spk-001" / "features.jsonl"
    with pytest.raises(manifest.ManifestError, match="licence note"):
        manifest.guard(items, out, private)
    note = private / "spk-001" / "LICENCE.txt"
    note.parent.mkdir()
    note.write_text("   \n")
    with pytest.raises(manifest.ManifestError, match="licence note"):  # an empty note is not one
        manifest.guard(items, out, private)
    note.write_text("Read in full on 1 Dec 2026; (a) (b) (c) answered.\n")
    manifest.guard(items, out, private)  # now allowed
    with pytest.raises(manifest.ManifestError, match="under"):
        manifest.guard(items, tmp_path / "elsewhere.jsonl", private)
    own = manifest.load(write_manifest(tmp_path, make(tmp_path)))
    with pytest.raises(manifest.ManifestError, match="under"):  # own recordings stay private too
        manifest.guard(own, tmp_path / "elsewhere.jsonl", private)


WORDS = {
    "model": "scripted",
    "revision": "r",
    "words": [
        {"word": "I", "start": 0.6, "end": 0.7, "probability": 0.9},
        {"word": "live", "start": 0.8, "end": 1.0, "probability": 0.9},
        {"word": "here", "start": 1.1, "end": 1.4, "probability": 0.9},
    ],
}


def scripted(calls: list[bytes] | None = None) -> Any:
    def run(audio: bytes) -> dict[str, Any]:
        if calls is not None:
            calls.append(audio)
        return WORDS

    return run


def lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_extraction_writes_a_row_per_recording_and_resumes(tmp_path: Path) -> None:
    items = manifest.load(write_manifest(tmp_path, make(tmp_path, asked_seconds="40")))
    out = tmp_path / "out" / "features.jsonl"
    calls: list[bytes] = []
    first = extract.run(items, out, scripted(calls), None, None)
    assert first == {"done": 3, "failed": 0, "skipped": 0} and len(calls) == 3
    rows = lines(out)
    assert [r["id"] for r in rows] == ["r0", "r1", "r2"] and rows[0]["score"] == 3.5
    f = rows[0]["features"]
    assert f["words"] == 3.0 and f["share_of_time"] == pytest.approx(0.01, abs=0.01)
    assert f["mtld"] is None  # no language step was given
    again = extract.run(items, out, scripted(calls), None, None)
    assert again == {"done": 0, "failed": 0, "skipped": 3} and len(calls) == 3  # nothing redone


def test_a_supplied_transcript_skips_recognition(tmp_path: Path) -> None:
    rows = make(tmp_path, n=1, words="t0.json")
    (tmp_path / "t0.json").write_text(json.dumps(WORDS))
    items = manifest.load(write_manifest(tmp_path, rows))
    out = tmp_path / "f.jsonl"
    assert extract.run(items, out, None, None, None)["done"] == 1  # no service needed


def test_an_unreadable_recording_is_a_failed_row_and_is_tried_again(tmp_path: Path) -> None:
    rows = make(tmp_path, n=2)
    (tmp_path / "a0.wav").write_bytes(b"not a wav")
    items = manifest.load(write_manifest(tmp_path, rows))
    out = tmp_path / "f.jsonl"
    counts = extract.run(items, out, scripted(), None, None)
    assert counts == {"done": 1, "failed": 1, "skipped": 0}
    failed = next(r for r in lines(out) if r["id"] == "r0")
    assert "audio" in failed["failed"] and "ffmpeg" in failed["failed"]
    assert extract.done_ids(out) == {"r1"}  # a failed row is not done
    (tmp_path / "a0.wav").write_bytes(speech_like())  # fixed: the next run redoes only it
    again = extract.run(items, out, scripted(), None, None)
    assert again == {"done": 1, "failed": 0, "skipped": 1}
    assert extract.done_ids(out) == {"r0", "r1"}


def test_a_refusal_fails_the_row_but_a_service_that_is_down_stops_the_run(
    tmp_path: Path,
) -> None:
    items = manifest.load(write_manifest(tmp_path, make(tmp_path)))
    out = tmp_path / "f.jsonl"

    def refuse(_: bytes) -> dict[str, Any]:
        raise Refused("400: bad audio")

    assert extract.run(items, out, refuse, None, None)["failed"] == 3
    n = 0

    def flaky(_: bytes) -> dict[str, Any]:
        nonlocal n
        n += 1
        if n == 2:
            raise Unavailable("starting")
        return WORDS

    out2 = tmp_path / "g.jsonl"
    with pytest.raises(Unavailable):
        extract.run(items, out2, flaky, None, None)
    assert extract.done_ids(out2) == {"r0"}  # what was done is kept, the run can resume


def test_the_command_checks_a_manifest_and_refuses_a_bad_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    good = write_manifest(tmp_path, make(tmp_path))
    assert main(["check", str(good)]) == 0
    assert "3 recordings" in capsys.readouterr().out
    rows = make(tmp_path)
    rows[1]["id"] = "r0"
    bad = write_manifest(tmp_path, rows)
    assert main(["check", str(bad)]) == 2
    assert "repeated" in capsys.readouterr().err
    corpus = write_manifest(tmp_path, make(tmp_path, source="corpus"))
    assert main(["extract", str(corpus), "--out", str(tmp_path / "x.jsonl")]) == 2
    assert "under" in capsys.readouterr().err  # outside data/private: refused before any work
