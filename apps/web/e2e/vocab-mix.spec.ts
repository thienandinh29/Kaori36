import { expect, test } from "@playwright/test";

// New words mixed across levels by default (specs/vocabulary, levels): the "Trộn A1–C1" choice
// asks for every level up to C1, which the server interleaves; a single level is still one tap away.
test("new words mix every level by default, and one level can still be chosen", async ({
  page,
}) => {
  await page.addInitScript(() => {
    localStorage.removeItem("nodetrail_english_learner");
    localStorage.removeItem("nodetrail_vocab_level");
  });
  const asked: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("vocab/session")) asked.push(r.url());
  });
  await page.goto("/tu-vung");
  const mix = page.getByRole("button", { name: /Trộn A1–C1/ });
  await expect(mix).toHaveAttribute("aria-pressed", "true");
  await expect.poll(() => asked.at(-1) ?? "").toContain("max_level=C1");
  expect(asked.at(-1)).not.toContain("level=B1");
  await page.getByRole("button", { name: /^B1/ }).click();
  await expect(mix).toHaveAttribute("aria-pressed", "false");
  await expect.poll(() => asked.at(-1) ?? "").toContain("&level=B1");
});
