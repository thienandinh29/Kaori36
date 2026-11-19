import { describe, expect, it } from "vitest";
import { DataError } from "@/lib/decode";
import {
  highlight,
  keyText,
  parsePassageReview,
  parseQueue,
  parseReviewTexts,
  shortcut,
} from "./review";

const queue = {
  counts: { needs_review: 1, verified: 0, approved: 2, rejected: 0 },
  items: [
    {
      id: "bees-mcq-1",
      text: "bees",
      kind: "mcq",
      skill: "detail",
      question: {
        stem: "What do bees eat?",
        options: ["Nectar", "Stored honey", "Pollen"],
      },
      key: 1,
      evidence: ["They eat the honey."],
      checker_answer: "A",
      checker_model: "baidu/ernie:free",
      note: null,
      passage: "Bees work.  They eat the\nhoney. In summer they fly.",
    },
  ],
};

describe("reading review (step 4.2c)", () => {
  it("decodes the queue and refuses missing counts", () => {
    const q = parseQueue(queue);
    expect(q.counts.approved).toBe(2);
    expect(q.items[0]?.checkerAnswer).toBe("A");
    expect(() =>
      parseQueue({ ...queue, counts: { needs_review: 1 } }),
    ).toThrow();
  });

  it("highlights evidence across line breaks and extra spaces", () => {
    const item = parseQueue(queue).items[0]!;
    const parts = highlight(item.passage!, item.evidence);
    expect(parts.filter((p) => p.evidence).map((p) => p.text)).toEqual([
      "They eat the\nhoney.",
    ]);
    expect(parts.map((p) => p.text).join("")).toBe(item.passage);
    expect(highlight("No match here.", ["Absent."])).toEqual([
      { text: "No match here.", evidence: false },
    ]);
  });

  it("shows keys the way the owner reads them", () => {
    const item = parseQueue(queue).items[0]!;
    expect(keyText(item)).toBe("B. Stored honey");
    expect(keyText({ ...item, kind: "tfng", key: "not_given" })).toBe(
      "NOT GIVEN",
    );
    expect(
      keyText({ ...item, kind: "completion", key: ["honey", "the honey"] }),
    ).toBe("honey / the honey");
    expect(
      keyText({ ...item, kind: "headings", key: { "0": 2, "1": 0 } }),
    ).toBe("0:2, 1:0");
  });
});

describe("review by passage (step 4.2f)", () => {
  const item = {
    id: "bees-tfng-1",
    text: "bees",
    kind: "tfng",
    skill: "detail",
    question: { statement: "Bees live alone." },
    key: "false",
    evidence: ["Honey bees live in large colonies."],
    checker_answer: "FALSE",
    checker_model: "baidu/ernie",
    note: null,
    agreed: true,
  };
  it("decodes the text list with the owner's stats", () => {
    expect(
      parseReviewTexts({
        texts: [{ slug: "bees", title: "Bees", agreed: 3, flagged: 1 }],
        stats: { decisions: 4, median_seconds: 21, overturned: 1 },
      }),
    ).toEqual({
      texts: [{ slug: "bees", title: "Bees", agreed: 3, flagged: 1 }],
      stats: { decisions: 4, medianSeconds: 21, overturned: 1 },
    });
    expect(() =>
      parseReviewTexts({
        texts: [{ slug: "b", title: "B", agreed: -1, flagged: 0 }],
        stats: { decisions: 0, median_seconds: null, overturned: 0 },
      }),
    ).toThrow(DataError);
  });
  it("decodes a passage and its items without a per-item passage", () => {
    const r = parsePassageReview({
      slug: "bees",
      title: "Bees",
      passage: "Honey bees live in large colonies.",
      items: [item],
    });
    expect(r.items[0]).toMatchObject({ id: "bees-tfng-1", agreed: true });
    expect("passage" in r.items[0]!).toBe(false);
    expect(() =>
      parsePassageReview({
        slug: "b",
        title: "B",
        passage: "x",
        items: [{ ...item, agreed: "yes" }],
      }),
    ).toThrow(DataError);
  });
  it("maps keys to actions, with reasons only while rejecting", () => {
    expect(shortcut("a", false)).toEqual({ type: "approve" });
    expect(shortcut("A", false)).toEqual({ type: "approve" });
    expect(shortcut("r", false)).toEqual({ type: "reject" });
    expect(shortcut("s", false)).toEqual({ type: "skip" });
    expect(shortcut("ArrowRight", false)).toEqual({ type: "skip" });
    expect(shortcut("ArrowLeft", false)).toEqual({ type: "back" });
    expect(shortcut("2", false)).toBeNull();
    expect(shortcut("2", true)).toEqual({
      type: "reason",
      reason: "not_answerable",
    });
    expect(shortcut("6", true)).toBeNull();
    expect(shortcut("a", true)).toBeNull(); // no approving mid-reject
    expect(shortcut("Enter", true)).toEqual({ type: "confirm" });
    expect(shortcut("Escape", true)).toEqual({ type: "cancel" });
  });
});
