import { expect, test, type Page, type Route } from "@playwright/test";

// A Reading test taken outside the app (specs/listening-reading/step-4.3d.md).
const LEARNER =
  process.env.E2E_LEARNER_ID ?? "00000000-0000-4000-8000-0000000e2e01";
const PASSAGE =
  "The River Thames flows through London. By 1957 it was declared biologically dead.\n\nA cleanup programme began in the 1960s. Seals are often seen near the estuary.";
const QUESTIONS =
  "1 The Thames was declared dead in 1957.\n2 Seals are often seen\nA in central London.\nB near the estuary.\nC in the 1950s.";

async function asLearner(page: Page) {
  await page.addInitScript((value) => {
    localStorage.setItem("nodetrail_english_learner", value);
  }, LEARNER);
}

async function paste(page: Page) {
  await page.getByLabel(/^Bài đọc/).fill(PASSAGE);
  await page.getByLabel(/^Câu hỏi/).fill(QUESTIONS);
  await page.getByLabel(/^Đáp án chính thức/).fill("1 TRUE 2 B");
  await page.getByLabel(/^Câu trả lời của bạn/).fill("1 TRUE 2 A");
  const consent = page.getByLabel("Tôi đã đọc và đồng ý");
  if (await consent.count()) await consent.check();
  await page.getByRole("button", { name: "Gửi để chấm" }).click();
}

test("the card on /doc opens the page", async ({ page }) => {
  await asLearner(page);
  await page.goto("/doc");
  await page.getByRole("link", { name: "Chấm bài bạn tự làm" }).click();
  await expect(page).toHaveURL(/\/doc\/bai-cua-ban$/);
  await expect(
    page.getByRole("heading", { name: "Chấm bài Reading bạn tự làm" }),
  ).toBeVisible();
});

test("a pasted test reaches the server and the worker (real API)", async ({
  page,
}) => {
  await asLearner(page);
  await page.goto("/doc/bai-cua-ban");
  await paste(page);
  // CI's stack has no model key, so the worker says why it could not read the questions;
  // with a key the list to check appears instead. Either is the real server's answer.
  await expect(
    page
      .getByText("chưa bật mô hình", { exact: false })
      .or(page.getByTestId("own-confirm")),
  ).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Xóa bài này" }).click();
  await expect(page.getByText("Đã xóa.")).toBeVisible();
});

test("paste, check the questions, see the mark and the explained trap", async ({
  page,
}) => {
  await asLearner(page);
  const confirmed: unknown[] = [];
  const question = (over: Record<string, unknown>) => ({
    options: [],
    max_words: null,
    problems: [],
    ...over,
  });
  const parsed = {
    id: "00000000-0000-4000-8000-00000000aa01",
    status: "parsed",
    passage: PASSAGE,
    progress_test: false,
    failure_vi: null,
    result: null,
    questions: [
      question({
        number: 1,
        kind: "tfng",
        text: "The Thames was declared dead in 1957.",
        key: "TRUE",
        answer: "TRUE",
      }),
      question({
        number: 2,
        kind: "mcq",
        text: "Seals are often seen",
        options: ["in central London.", "near the estuary.", "in the 1950s."],
        key: "B",
        answer: "A",
      }),
    ],
  };
  const done = {
    ...parsed,
    status: "done",
    result: {
      correct: 1,
      total: 2,
      answered: 2,
      unsupported: [],
      evidence: 2,
      explained: true,
      marks: [
        {
          number: 1,
          kind: "tfng",
          answer: "TRUE",
          answer_text: "TRUE",
          correct: true,
          trap: null,
          key: "TRUE",
          explanation: null,
          explanation_vi: null,
        },
        {
          number: 2,
          kind: "mcq",
          answer: "A",
          answer_text: "A. in central London.",
          correct: false,
          trap: "wrong_part",
          key: "B. near the estuary.",
          explanation: {
            key_quotes: ["Seals are often seen near the estuary"],
            why_key_vi: "Bài đọc nói hải cẩu thường được thấy gần cửa sông.",
            why_wrong_vi: "Bài có nhắc London nhưng không nói hải cẩu ở đó.",
            wrong_quotes: ["flows through London"],
          },
          explanation_vi: null,
        },
      ],
    },
  };
  let polls = 0;
  await page.route(
    "**/api/backend/reading/own-tests**",
    async (route: Route) => {
      const req = route.request();
      const url = new URL(req.url());
      const json = (b: unknown, status = 200) =>
        route.fulfill({
          status,
          contentType: "application/json",
          body: JSON.stringify(b),
        });
      if (req.method() === "POST" && url.pathname.endsWith("/own-tests"))
        return json({ id: parsed.id, status: "queued" }, 202);
      if (req.method() === "POST" && url.pathname.endsWith("/confirm")) {
        confirmed.push(req.postDataJSON());
        return json(done);
      }
      if (url.pathname.endsWith("/own-tests")) return json([]);
      polls += 1; // the first look finds it still being read
      return json(
        polls === 1 ? { ...parsed, status: "parsing", questions: [] } : parsed,
      );
    },
  );
  await page.goto("/doc/bai-cua-ban");
  await paste(page);
  await expect(page.getByText("Đang đọc câu hỏi…")).toBeVisible();
  const check = page.getByTestId("own-confirm");
  await expect(check).toBeVisible();
  await expect(check.getByTestId("own-q-2")).toContainText("Bạn trả lời: A");
  await page.getByRole("button", { name: "Xác nhận và chấm" }).click();

  const result = page.getByTestId("own-result");
  await expect(result.getByRole("heading")).toHaveText("Đúng 1/2 câu");
  const wrong = result.getByTestId("own-mark-2");
  await expect(wrong).toContainText("Đúng ở chỗ khác trong bài");
  await expect(wrong).toContainText("Giải thích tự động, chưa kiểm chứng");
  await expect(wrong).toContainText("Seals are often seen near the estuary");
  expect(confirmed).toHaveLength(1);
  expect(
    (confirmed[0] as { questions: { number: number; key: string }[] })
      .questions[1],
  ).toMatchObject({ number: 2, key: "B" });
});
