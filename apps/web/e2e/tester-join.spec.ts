import { expect, test } from "@playwright/test";

// A tester's invite link (specs/speaking/step-5.5.md). The API is mocked: the link is used by the button, not by
// opening the page, and while recording is shut the tester is told so.
const TOKEN = "a".repeat(43);
const TESTER = "77777777-7777-4777-8777-777777777777";

test("opening the link spends nothing; the button signs in and says recording is still closed", async ({
  page,
}) => {
  let redeemed = 0;
  let research = 0;
  await page.route("**/api/backend/testers/redeem", async (route) => {
    redeemed += 1;
    await route.fulfill({
      json: {
        learner_id: TESTER,
        label: "Mai",
        may_record: false,
        research_notice: "research-v1",
        research_consented: false,
      },
    });
  });
  await page.route("**/api/backend/testers/research-consent", async (route) => {
    research += 1;
    await route.fulfill({ status: 204, body: "" });
  });
  await page.goto(`/vao/${TOKEN}`);
  await expect(page.getByTestId("join")).toBeVisible();
  await expect(page.getByText("Bản nháp", { exact: false })).toBeVisible();
  expect(redeemed).toBe(0); // a link preview would not have used it
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Bắt đầu" }).click();
  await expect(page.getByTestId("join-done")).toBeVisible();
  await expect(
    page.getByText("Phần ghi âm chưa mở cho người thử", { exact: false }),
  ).toBeVisible();
  expect(redeemed).toBe(1);
  expect(research).toBe(1);
  const stored = await page.evaluate(() =>
    localStorage.getItem("nodetrail_english_learner"),
  );
  expect(stored).toBe(TESTER);
});

test("a used or expired link says so", async ({ page }) => {
  await page.route("**/api/backend/testers/redeem", async (route) => {
    await route.fulfill({ status: 404, json: { detail: "gone" } });
  });
  await page.goto(`/vao/${TOKEN}`);
  await page.getByRole("button", { name: "Bắt đầu" }).click();
  await expect(page.getByTestId("join-bad")).toBeVisible();
});

test("a link that is not a token is not found", async ({ page }) => {
  const r = await page.goto("/vao/short");
  expect(r?.status()).toBe(404);
});

test("a refused start (daily limit) shows the plain message", async ({
  page,
}) => {
  await page.addInitScript((id) => {
    localStorage.setItem("nodetrail_english_learner", id);
    localStorage.setItem("nodetrail_speaking_consent", "speaking-v1");
  }, TESTER);
  await page.route("**/api/backend/speaking/tests?**", async (route) => {
    await route.fulfill({
      json: {
        can_record: true,
        consent: "speaking-v1",
        tests: [
          {
            id: "t01",
            title: "Home",
            draft: true,
            questions: 18,
            practice: [],
          },
        ],
        practices: [],
        max_tries: 3,
        past: [],
        left_today: { mock_tests: 0, practice_tries: 5 },
      },
    });
  });
  await page.route("**/api/backend/speaking/tests", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await route.fulfill({
      status: 429,
      json: { detail: "Hôm nay bạn đã thi thử đủ 3 bài. Mai quay lại nhé." },
    });
  });
  await page.goto("/noi/thi");
  await expect(page.getByTestId("left-today")).toContainText("0 bài thi thử");
});
