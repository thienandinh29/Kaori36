import { describe, expect, it } from "vitest";
import { highlight, keyText, parseQueue } from "./review";

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
