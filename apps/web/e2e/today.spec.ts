import { expect, test } from "@playwright/test";

// Two maps, M3: the home page's "Hôm nay" list from the real API and engine.
const LEARNER =
  process.env.E2E_LEARNER_ID ?? "00000000-0000-4000-8000-0000000e2e01";

test("today's list shows activities with a reason and in-app links", async ({
  page,
}) => {
  await page.addInitScript((value) => {
    localStorage.setItem("nodetrail_english_learner", value);
  }, LEARNER);
  await page.goto("/");
  const list = page.getByTestId("today-list");
  await expect(list.getByRole("heading", { name: "Hôm nay" })).toBeVisible();
  await expect(list.getByText("Mục tiêu: IELTS 7,0")).toBeVisible();
  const items = list.locator("ol > li");
  expect(await items.count()).toBeGreaterThanOrEqual(1);
  const first = items.first();
  const href = await first
    .getByRole("link", { name: "Bắt đầu" })
    .getAttribute("href");
  expect(href).toMatch(/^\/[a-z-]/);
  await first.getByText("Vì sao?").click();
  await expect(first.locator("details p").first()).not.toBeEmpty();
  await expect(list.getByText("đề xuất", { exact: false })).toBeVisible();
});
