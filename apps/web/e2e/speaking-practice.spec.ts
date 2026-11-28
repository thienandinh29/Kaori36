import { expect, test, type Page } from "@playwright/test";

// Guided Speaking practice (specs/speaking/step-5.4b.md) with Chromium's fake microphone, the timing
// shortened by the test-only speed setting (nodetrail_exam_speed). Owner only.
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

test("a Part 3 question is built with ideas, spoken, and repeated twice with less time", async ({
  page,
}) => {
  test.setTimeout(150_000);
  await asLearner(page, LEARNER);
  await page.goto("/noi/luyen");
  const home = page.getByTestId("speaking-practice");
  await expect(
    home.getByRole("heading", { name: "Luyện nói có hướng dẫn" }),
  ).toBeVisible({ timeout: 20_000 });
  const agree = home.getByLabel("Tôi đã đọc và đồng ý");
  if (await agree.count()) await agree.click();
  await home.locator("summary").first().click();
  const part3 = home.locator("li", { hasText: "Phần 3" }).first();
  await part3.getByRole("button", { name: "Luyện câu này" }).click();

  // try 1: 60 s. The help is there before speaking, and gone while speaking.
  const runner = page.getByTestId("practice-runner");
  await expect(
    runner.getByRole("heading", { name: "Lần 1 · 60 giây" }),
  ).toBeVisible();
  await expect(runner.getByTestId("ideas")).toContainText("Khung ý");
  await expect(runner.getByTestId("ideas")).toContainText(
    "Nói vì sao điều đó quan trọng",
  );
  await expect(runner.getByTestId("ideas")).toContainText("tourism");
  await runner.getByRole("button", { name: "Bắt đầu nói (60 giây)" }).click();
  await expect(runner.getByText("Đang ghi", { exact: false })).toBeVisible({
    timeout: 20_000,
  });
  await expect(runner.getByTestId("ideas")).toHaveCount(0); // no help while speaking
  await expect(runner.getByText("điểm", { exact: false })).toHaveCount(0);

  const result = page.getByTestId("practice-result");
  await expect(result).toBeVisible({ timeout: 30_000 });
  await expect(
    result.getByText("Lần đầu: số đo này được lưu làm bằng chứng"),
  ).toBeVisible();

  // try 2: 45 s, and try 3: 30 s, with the repeats marked as practice
  await result
    .getByRole("button", { name: "Nói lại câu này (45 giây)" })
    .click();
  await expect(
    runner.getByRole("heading", { name: "Lần 2 · 45 giây" }),
  ).toBeVisible();
  await runner.getByRole("button", { name: "Bắt đầu nói (45 giây)" }).click();
  await expect(result).toBeVisible({ timeout: 30_000 });
  await result
    .getByRole("button", { name: "Nói lại câu này (30 giây)" })
    .click();
  await expect(
    runner.getByRole("heading", { name: "Lần 3 · 30 giây" }),
  ).toBeVisible();
  await runner.getByRole("button", { name: "Bắt đầu nói (30 giây)" }).click();
  await expect(result.getByText("Đã đủ 3 lần cho câu này.")).toBeVisible({
    timeout: 30_000,
  });

  await expect(result.getByTestId("practice-try")).toHaveCount(3);
  await expect(
    result.getByText("Nói lại là luyện tập, không tính làm bằng chứng"),
  ).toHaveCount(2);
  await expect(
    result.getByRole("button", { name: /Nói lại câu này/ }),
  ).toHaveCount(0);

  page.once("dialog", (d) => void d.accept());
  await result.getByRole("button", { name: "Xóa lần luyện này" }).click();
  await page.waitForURL(/\/noi\/luyen$/);
});

test("other learners cannot practise yet", async ({ page }) => {
  await asLearner(page, null);
  await page.goto("/noi/luyen");
  await expect(
    page.getByText("Ghi âm hiện chỉ mở cho chủ dự án", { exact: false }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Luyện câu này" })).toHaveCount(
    0,
  );
});

test("a practice page shows the numbers of the tries side by side, with no verdict (mocked)", async ({
  page,
}) => {
  const id = "66666666-6666-4666-8666-666666666666";
  const measures = (
    rate: number,
    pauses: number,
    run: number,
    share: number,
  ) => ({
    words: 40,
    speaking_seconds: 20,
    short: false,
    speech_rate: rate,
    articulation_rate: rate + 20,
    pauses: {
      count: 5,
      per_minute: pauses,
      between_clauses: 3,
      inside_clause: 2,
      long: 0,
      longest_seconds: 1.4,
    },
    fillers: { count: 1 },
    longest_run: { words: run, seconds: 5 },
    asked_seconds: 60,
    share_of_time: share,
  });
  const answer = (n: number, m: ReturnType<typeof measures>) => ({
    id: `7777777${n}-7777-4777-8777-777777777777`,
    seconds: 20,
    problems: [],
    audio: false,
    delete_after: null,
    transcript: "done",
    text: "I think travel is good.",
    words: [],
    measures: m,
    language: null,
  });
  await asLearner(page, LEARNER);
  await page.route(`**/api/backend/speaking/practice/${id}?*`, (route) =>
    route.fulfill({
      json: {
        id,
        keep: false,
        test_id: "t01",
        title: "Home, music and a journey",
        question: {
          id: "p3-1",
          part: 3,
          text: "Why do some people prefer to travel alone?",
        },
        cue_card: null,
        theme: "travel and transport",
        words: ["tourism", "traffic", "pollution", "crowded", "transport"],
        max_tries: 3,
        next_seconds: 30,
        tries: [
          {
            id,
            try_no: 1,
            asked_seconds: 60,
            finished: true,
            counts_as_evidence: true,
            answer: answer(1, measures(90, 12, 8, 0.33)),
          },
          {
            id: "88888888-8888-4888-8888-888888888888",
            try_no: 2,
            asked_seconds: 45,
            finished: true,
            counts_as_evidence: false,
            answer: answer(2, measures(118, 6, 15, 0.71)),
          },
        ],
      },
    }),
  );
  await page.goto(`/noi/luyen/${id}`);
  const compare = page.getByTestId("compare");
  await expect(compare).toContainText("Tốc độ (từ/phút)");
  const row = compare.getByRole("row", { name: /Tốc độ/ });
  await expect(row).toContainText("90");
  await expect(row).toContainText("118");
  await expect(
    compare.getByRole("row", { name: /Lần ngắt mỗi phút/ }),
  ).toContainText("12");
  await expect(
    compare.getByRole("row", { name: /Phần thời gian/ }),
  ).toContainText("71%");
  await expect(
    compare.getByRole("columnheader", { name: "Lần 2" }),
  ).toBeVisible();
  await expect(compare).toContainText("không có đánh giá tốt hay xấu");
  await expect(
    page
      .getByTestId("practice-result")
      .getByText(/điểm số|band|Band|tốt hơn|tiến bộ/),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Nói lại câu này (30 giây)" }),
  ).toBeVisible();
});
