import { expect, test } from "@playwright/test";

// Dictionary search over the word list (specs/vocabulary/step-dictionary.md), on the real API.
test("look a word up in English and in Vietnamese", async ({ page }) => {
  await page.goto("/tu-dien");
  await expect(page.getByRole("heading", { name: "Từ điển" })).toBeVisible();
  const box = page.getByLabel("Từ cần tra");
  await box.fill("important");
  const first = page.locator(".en-word").first();
  await expect(first.locator("strong")).toHaveText("important");
  await expect(first.getByText("quan trọng")).toBeVisible();
  await expect(page.getByText("Bản nháp", { exact: true })).toBeVisible();
  await box.fill("quan trọng");
  await expect(page.getByTestId("dictionary-count")).toHaveText(/kết quả/);
  await box.fill("zzzqqq");
  await expect(page.getByTestId("dictionary-count")).toHaveText(
    "Không có từ này trong danh sách của NodeTrail.",
  );
});
