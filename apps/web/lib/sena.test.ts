import { describe, expect, it } from "vitest";
import { SENA_POSES, senaSvg } from "./sena";

describe("Sena", () => {
  it("draws every pose as one labelled SVG with its own clip path", () => {
    for (const pose of SENA_POSES) {
      const s = senaSvg(pose, "s1", "Sena");
      expect(s.startsWith("<svg")).toBe(true);
      expect(s).toContain(`sena--${pose}`);
      expect(s).toContain('id="s1-body"');
      expect(s).toContain("url(#s1-body)");
      expect(s).toContain('role="img"');
    }
  });
  it("gives the reactions their props", () => {
    expect(senaSvg("think", "a", "x")).toContain(">?</text>");
    expect(senaSvg("heart", "a", "x")).toContain("#ef6f86");
    expect(senaSvg("oops", "a", "x")).toContain("#79c4ea");
  });
  it("escapes the label", () => {
    expect(senaSvg("idle", "a", 'Sena "<b>"')).toContain(
      'aria-label="Sena &quot;&lt;b>&quot;"',
    );
  });
});
