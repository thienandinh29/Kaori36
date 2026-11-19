import { expect, test, type Page } from "@playwright/test";

// Timed Reading tests (specs/listening-reading/step-4.3b.md), on mocked API calls.
const LEARNER =
  process.env.E2E_LEARNER_ID ?? "00000000-0000-4000-8000-0000000e2e01";
const TEST_ID = "0b7e3c1e-0000-4000-8000-000000000001";
const PASSAGE =
  "Honey bees live in large colonies.\n\nWorker bees collect nectar.\n\nIn winter the bees stay together.";

async function asLearner(page: Page) {
  await page.addInitScript((value) => {
    localStorage.setItem("nodetrail_english_learner", value);
  }, LEARNER);
}

test("a timed test is answered, submitted and marked without feedback before", async ({
  page,
}) => {
  await asLearner(page);
  let submitted: Record<string, unknown> | null = null;
  const json = (b: unknown) => ({
    contentType: "application/json",
    body: JSON.stringify(b),
  });
  await page.route("**/api/backend/reading/texts/bees/tests", (route) =>
    route.fulfill(
      json({
        test_id: TEST_ID,
        limit_seconds: 1200,
        started_at: "2026-11-20T09:00:00Z",
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
            id: "bees-mcq-1",
            kind: "mcq",
            skill: "detail",
            stem: "What do workers collect?",
            options: ["Pollen", "Nectar", "Water"],
          },
          {
            id: "bees-completion-1",
            kind: "completion",
            skill: "detail",
            sentence: "In winter the bees stay ___.",
            max_words: 1,
          },
        ],
      }),
    ),
  );
  await page.route(
    `**/api/backend/reading/tests/${TEST_ID}/submit`,
    (route) => {
      submitted = route.request().postDataJSON();
      return route.fulfill(
        json({
          test_id: TEST_ID,
          correct: 1,
          total: 3,
          answered: 2,
          over_time: false,
          seconds: 312,
          items: [
            {
              id: "bees-tfng-1",
              answer: "TRUE",
              correct: false,
              key: "FALSE",
              evidence: ["Honey bees live in large colonies."],
              at_seconds: 20,
            },
            {
              id: "bees-mcq-1",
              answer: 1,
              correct: true,
              key: "B. Nectar",
              evidence: ["Worker bees collect nectar."],
              at_seconds: 41,
            },
            {
              id: "bees-completion-1",
              answer: null,
              correct: false,
              key: "together",
              evidence: ["In winter the bees stay together."],
              at_seconds: null,
            },
          ],
        }),
      );
    },
  );
  await page.goto("/doc/bees/thi");
  const card = page.getByTestId("reading-test");
  await expect(card.getByRole("timer")).toContainText("20:00");
  const qs = page.getByTestId("reading-test-question");
  await expect(qs).toHaveCount(3);
  await qs.nth(0).getByRole("radio", { name: "TRUE", exact: true }).click();
  await qs
    .nth(1)
    .getByRole("radio", { name: /Nectar/ })
    .click();
  await expect(card.getByRole("timer")).toContainText("2/3");
  // Nothing is graded before submitting.
  await expect(page.locator(".en-feedback")).toHaveCount(0);
  page.once("dialog", (d) => d.accept()); // one question left blank
  await card.getByRole("button", { name: "Nộp bài" }).click();
  const result = page.getByTestId("reading-test-result");
  await expect(result).toContainText("Đúng 1/3 câu");
  await expect(result).toContainText("không phải band IELTS");
  await expect(qs.nth(0)).toContainText("FALSE");
  await expect(qs.nth(2)).toContainText("bỏ trống");
  await expect(page.locator("mark").first()).toHaveText(
    "Honey bees live in large colonies.",
  );
  expect(submitted).not.toBeNull();
  const body = submitted as unknown as {
    learner_id: string;
    answers: Record<string, { answer: unknown; at_seconds: number }>;
  };
  expect(body.learner_id).toBe(LEARNER);
  expect(Object.keys(body.answers)).toEqual(["bees-tfng-1", "bees-mcq-1"]);
  expect(body.answers["bees-tfng-1"]!.answer).toBe("TRUE");
  expect(body.answers["bees-mcq-1"]!.answer).toBe(1);
  expect(typeof body.answers["bees-mcq-1"]!.at_seconds).toBe("number");
});

test("a text with nothing served shows a problem, not a test (real API)", async ({
  page,
}) => {
  await asLearner(page);
  await page.goto("/doc/no-such-text/thi");
  await expect(page.getByTestId("reading-test")).toHaveCount(0); // 404 from the API: a problem shown
});
