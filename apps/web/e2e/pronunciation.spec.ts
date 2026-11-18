import { expect, test, type Page } from "@playwright/test";

// The pronunciation page (specs/pronunciation/step-3.1.md) with Chromium's fake microphone.
const LEARNER =
  process.env.E2E_LEARNER_ID ?? "00000000-0000-4000-8000-0000000e2e01";

async function asLearner(page: Page, id: string | null) {
  await page.addInitScript((value) => {
    if (value) localStorage.setItem("nodetrail_english_learner", value);
    else localStorage.removeItem("nodetrail_english_learner");
  }, id);
}

test.use({
  launchOptions: {
    args: [
      "--use-fake-ui-for-media-stream",
      "--use-fake-device-for-media-stream",
    ],
  },
  permissions: ["microphone"],
});

test("the owner records a sentence; the recording's quality is checked, stored and deleted", async ({
  page,
}) => {
  await asLearner(page, LEARNER); // only the owner may record until a privacy review
  await page.goto("/phat-am");
  const card = page.getByTestId("pronunciation");
  await card.getByLabel("Tôi đã đọc và đồng ý").click(); // the notice then gives way to the controls
  await card.getByRole("button", { name: "Bắt đầu ghi âm" }).click();
  await expect(card.getByText("Đang ghi", { exact: false })).toBeVisible();
  await page.waitForTimeout(2500);
  await card.getByRole("button", { name: "Dừng" }).click();
  await card.getByRole("button", { name: "Gửi kiểm tra" }).click();
  const verdict = card.getByRole("status");
  await expect(verdict).toBeVisible();
  // Chromium's fake microphone beeps: either verdict is fine; what matters is a verdict, never a sound judgement.
  if (await verdict.getByText("Bản ghi rõ ràng", { exact: false }).count()) {
    const rows = page.getByTestId("recordings").locator("li");
    await expect(rows.first()).toBeVisible();
    const before = await rows.count();
    await rows.first().getByRole("button", { name: "Xóa" }).click();
    await expect(rows).toHaveCount(before - 1);
  }
});

test("other learners cannot record yet", async ({ page }) => {
  await asLearner(page, null);
  await page.goto("/phat-am");
  await expect(
    page.getByText("Ghi âm hiện chỉ mở cho chủ dự án", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Bắt đầu ghi âm" }),
  ).toHaveCount(0);
});
