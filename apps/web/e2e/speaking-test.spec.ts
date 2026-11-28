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

test("the result page shows the numbers of each answer and of the whole test, never a score (step 5.2)", async ({
  page,
}) => {
  const id = "11111111-1111-4111-8111-111111111111";
  const measures = {
    words: 24,
    speaking_seconds: 10.4,
    short: true,
    speech_rate: 139,
    articulation_rate: 167.1,
    pauses: {
      count: 3,
      per_minute: 17.3,
      between_clauses: 2,
      inside_clause: 1,
      long: 1,
      total_seconds: 4.1,
      longest_seconds: 2.2,
      unplaced: 0,
    },
    fillers: { count: 2 },
    longest_run: { words: 15, seconds: 4.6 },
    asked_seconds: 40,
    share_of_time: 0.26,
  };
  await asLearner(page, LEARNER);
  await page.route(`**/api/backend/speaking/tests/${id}?*`, (route) =>
    route.fulfill({
      json: {
        id,
        test_id: "t01",
        title: "Home, music and a journey",
        keep: false,
        started_at: "2026-11-28T09:00:00+00:00",
        finished_at: "2026-11-28T09:14:00+00:00",
        cue_card: {
          task: "Describe a journey.",
          points: ["a", "b", "c"],
          explain: "and why.",
        },
        part3_theme: "travel",
        questions: [
          {
            id: "p1-1-1",
            part: 1,
            text: "Do you live in a house or an apartment?",
            answer: {
              id: "22222222-2222-4222-8222-222222222222",
              seconds: 12.2,
              problems: [],
              audio: false,
              delete_after: null,
              transcript: "done",
              text: "Um, I live in a flat.",
              words: [],
              measures,
            },
          },
        ],
        summary: {
          answers: 1,
          words: 24,
          speaking_seconds: 10.4,
          speech_rate: 139,
          pauses_per_minute: 17.3,
          between_clauses: 2,
          inside_clause: 1,
          long: 1,
          fillers: 2,
          longest_run_words: 15,
        },
      },
    }),
  );
  await page.goto(`/noi/thi/${id}`);
  const line = page.getByTestId("exam-measures");
  await expect(line).toContainText("139 từ/phút");
  await expect(line).toContainText(
    "3 lần ngắt (2 giữa mệnh đề, 1 trong mệnh đề, 1 dài từ 2 giây)",
  );
  await expect(line).toContainText("2 từ đệm");
  await expect(line).toContainText("đoạn liền dài nhất 15 từ");
  await expect(line).toContainText("Dưới 15 giây nói");
  const summary = page.getByTestId("exam-summary");
  await expect(summary).toContainText("17.3 lần ngắt mỗi phút");
  await expect(summary).toContainText("Máy không biết vì sao bạn ngừng");
  await expect(
    page.getByTestId("exam-result").getByText(/điểm số|band|Band/),
  ).toHaveCount(0);
});
