import { expect, test, type Page } from "@playwright/test";

// The owner's Reading review queue (specs/listening-reading/step-4.2c.md).
const OWNER =
  process.env.E2E_LEARNER_ID ?? "00000000-0000-4000-8000-0000000e2e01";

async function asLearner(page: Page, id: string | null) {
  await page.addInitScript((value) => {
    if (value) localStorage.setItem("nodetrail_english_learner", value);
    else localStorage.removeItem("nodetrail_english_learner");
  }, id);
}

test("the owner sees the review queue with a tab per status", async ({
  page,
}) => {
  await asLearner(page, OWNER);
  await page.goto("/duyet-doc");
  const card = page.getByTestId("reading-review");
  await expect(
    card.getByRole("heading", { name: "Duyệt câu hỏi Đọc" }),
  ).toBeVisible();
  await expect(card.getByRole("tab")).toHaveCount(4);
  await card.getByRole("tab", { name: /Đã duyệt/ }).click();
  await expect(card.getByRole("tab", { name: /Đã duyệt/ })).toHaveAttribute(
    "aria-selected",
    "true",
  );
});

test("other learners cannot review", async ({ page }) => {
  await asLearner(page, null);
  await page.goto("/duyet-doc");
  await expect(
    page.getByText("Trang này chỉ dành cho chủ dự án.", { exact: false }),
  ).toBeVisible();
});
