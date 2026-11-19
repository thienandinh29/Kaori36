import { expect, test, type Page } from "@playwright/test";

// Reading practice, CP4 (specs/listening-reading/step-4.3.md).
const LEARNER =
  process.env.E2E_LEARNER_ID ?? "00000000-0000-4000-8000-0000000e2e01";
const PASSAGE =
  "Honey bees live in large colonies.\n\nWorker bees collect nectar.\n\nIn winter the bees stay together.";

async function asLearner(page: Page) {
  await page.addInitScript((value) => {
    localStorage.setItem("nodetrail_english_learner", value);
  }, LEARNER);
}

test("with no question served yet, the page says why (real API)", async ({
  page,
}) => {
  await asLearner(page);
  await page.goto("/doc");
  await expect(
    page.getByText("Chưa có bài đọc nào sẵn sàng", { exact: false }),
  ).toBeVisible();
});

test("a learner answers, sees the key and the deciding sentence", async ({
  page,
}) => {
  await asLearner(page);
  const posted: unknown[] = [];
  const trace = {
    kind: "bkt_update",
    concept_slug: "reading-detail",
    at: "2026-12-01T09:00:00Z",
    prior: 0.2,
    posterior: 0.1,
    evidence: {},
    rule: "reading.answer",
    rule_vi: "Đọc: tìm thông tin chi tiết: trả lời sai",
    alternatives: [],
  };
  await page.route("**/api/backend/reading/**", async (route) => {
    const url = new URL(route.request().url());
    const json = (b: unknown) =>
      route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(b),
      });
    if (url.pathname.endsWith("/reading/texts"))
      return json({
        texts: [{ slug: "bees", title: "Honey bees", questions: 2, words: 16 }],
      });
    if (url.pathname.endsWith("/reading/texts/bees"))
      return json({
        slug: "bees",
        title: "Honey bees",
        passage: PASSAGE,
        items: [
          {
            id: "bees-tfng-1",
            kind: "tfng",
            skill: "detail",
            statement: "Bees live alone.",
          },
          {
            id: "bees-headings-1",
            kind: "headings",
            skill: "main_idea",
            headings: ["Colonies", "Nectar", "Winter", "Enemies"],
            paragraphs: [0, 1, 2],
          },
        ],
      });
    posted.push(route.request().postDataJSON());
    return json(
      posted.length === 1
        ? {
            correct: false,
            score: 0,
            key: "FALSE",
            competency: "reading-detail",
            trace,
            evidence: ["Honey bees live in large colonies."],
          }
        : {
            correct: true,
            score: 1,
            key: "0: 0, 1: 1, 2: 2",
            competency: "reading-main-idea",
            trace,
            evidence: [],
          },
    );
  });
  await page.goto("/doc");
  await page.getByRole("link", { name: "Honey bees" }).click();
  const q = page.getByTestId("reading-question");
  await expect(q.getByText("Bees live alone.")).toBeVisible();
  await q.getByRole("button", { name: "TRUE", exact: true }).click();
  await expect(q.getByRole("status")).toContainText("Chưa đúng.");
  await expect(q.getByRole("status")).toContainText("FALSE");
  await expect(page.locator("mark")).toHaveText(
    "Honey bees live in large colonies.",
  );
  await q.getByRole("button", { name: "Câu tiếp" }).click();
  for (const [i, h] of [
    ["1", "1"],
    ["2", "2"],
    ["3", "3"],
  ] as const)
    await page.getByLabel(`Đoạn ${i}`).selectOption(h);
  await page.getByRole("button", { name: "Kiểm tra" }).click();
  await expect(page.getByRole("status")).toContainText("Đúng.");
  expect(posted).toEqual([
    { learner_id: LEARNER, answer: "TRUE" },
    { learner_id: LEARNER, answer: { "0": 0, "1": 1, "2": 2 } },
  ]);
  await page.getByRole("button", { name: "Xong" }).click();
  await expect(page.getByText("Bạn đã làm hết câu hỏi")).toBeVisible();
});
