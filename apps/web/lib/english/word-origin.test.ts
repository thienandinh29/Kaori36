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
  it("names TSL and BSL with their own authors, and says BSL definitions are machine-written", () => {
    const tsl = originLabels({ origin: "tsl", level: "B2", ipa: null });
    expect(tsl.level).toBe("B2 · ước lượng theo tần suất");
    expect(tsl.source).toContain("TSL 1.2 (Browne & Culligan");
    const bsl = originLabels({ origin: "bsl", level: "C1", ipa: null });
    expect(bsl.source).toContain("BSL 1.20");
    expect(bsl.source).toContain("Định nghĩa do máy viết");
    expect(bsl.source).not.toContain("Phillips");
  });
});
