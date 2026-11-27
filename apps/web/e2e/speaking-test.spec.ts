import { expect, test, type Page } from "@playwright/test";

// The Speaking examiner test (specs/speaking/step-5.4a.md) with Chromium's fake microphone, the timing
// shortened by the test-only speed setting (nodetrail_exam_speed), so a full test takes about half a minute.
const LEARNER =
  process.env.E2E_LEARNER_ID ?? "00000000-0000-4000-8000-0000000e2e01";

async function asLearner(page: Page, id: string | null) {
  await page.addInitScript((value) => {
    if (value) localStorage.setItem("nodetrail_english_learner", value);
    else localStorage.removeItem("nodetrail_english_learner");
    localStorage.setItem("nodetrail_exam_speed", "0.02");
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

test("the owner sits a whole test, replays the answers, then deletes it", async ({
  page,
}) => {
  test.setTimeout(150_000);
  await asLearner(page, LEARNER); // only the owner may record until a privacy review
  await page.goto("/noi/thi");
  const home = page.getByTestId("speaking-test");
  await expect(
    home.getByRole("heading", { name: "Các bài đã thi" }),
  ).toBeVisible();
  const agree = home.getByLabel("Tôi đã đọc và đồng ý");
  if (await agree.count()) await agree.click();

  await home.getByRole("button", { name: "Thử micro (3 giây)" }).click();
  await expect(
    home.getByTestId("mic-check").getByRole("status"),
  ).not.toHaveText("", { timeout: 15_000 });

  await home.getByRole("button", { name: "Bắt đầu thi" }).first().click();
  const exam = page.getByTestId("exam");
  await expect(exam.getByText("Phần 1")).toBeVisible();
  // Nothing is judged while speaking: no score, no hint, only the timer.
  await expect(exam.getByText("Đang ghi", { exact: false })).toBeVisible({
    timeout: 15_000,
  });
  await expect(exam.getByText("điểm", { exact: false })).toHaveCount(0);
  // Part 2 shows the cue card while preparing and speaking.
  await expect(exam.getByTestId("cue-card")).toBeVisible({ timeout: 60_000 });
  await expect(exam.getByText("Phần 3")).toBeVisible({ timeout: 60_000 });

  await page.waitForURL(/\/noi\/thi\/[0-9a-f-]{36}$/, { timeout: 90_000 });
  const result = page.getByTestId("exam-result");
  await expect(
    result.getByRole("heading", { name: "Nghe lại bài thi" }),
  ).toBeVisible();
  const answers = result.getByTestId("exam-answer");
  await expect(answers).toHaveCount(18);
  await expect(result.locator("audio")).toHaveCount(18); // every answer kept for a day
  await expect(
    result.getByText("Bản ghi tự xóa lúc", { exact: false }),
  ).toBeVisible();
  const audio = await page.request.get(
    (await result.locator("audio").first().getAttribute("src"))!,
  );
  expect(audio.headers()["content-type"]).toBe("audio/wav");

  page.once("dialog", (d) => void d.accept());
  await result.getByRole("button", { name: "Xóa bài thi này" }).click();
  await page.waitForURL(/\/noi\/thi$/);
});

test("other learners cannot sit the test yet", async ({ page }) => {
  await asLearner(page, null);
  await page.goto("/noi/thi");
  await expect(
    page.getByText("Ghi âm hiện chỉ mở cho chủ dự án", { exact: false }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Bắt đầu thi" })).toHaveCount(
    0,
  );
});
