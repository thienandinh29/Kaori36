import { describe, expect, it } from "vitest";
import { originLabels } from "./word-origin";

describe("originLabels", () => {
  it("leaves authored words as they were", () => {
    const l = originLabels({ origin: "authored", level: "B1", ipa: "/kɪk/" });
    expect(l.level).toBe("B1");
    expect(l.source).toBeNull();
  });
  it("marks imported words: estimated level, automatic IPA, the list and licence", () => {
    const l = originLabels({ origin: "nawl", level: "C1", ipa: null });
    expect(l.level).toBe("C1 · ước lượng theo tần suất");
    expect(l.ipaTitle).toContain("espeak-ng");
    expect(l.source).toContain("NAWL 1.2");
    expect(l.source).toContain("CC BY-SA 4.0");
  });
});
