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
  await card.getByRole("button", { name: "Theo trạng thái" }).click();
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

test("review by passage opens first, with the owner's own speed (real API)", async ({
  page,
}) => {
  await asLearner(page, OWNER);
  await page.goto("/duyet-doc");
  const list = page.getByTestId("review-texts");
  await expect(
    list.getByRole("heading", { name: "Bài đọc có câu hỏi chờ duyệt" }),
  ).toBeVisible();
  await expect(list.getByText(/Bạn (chưa|đã) duyệt/)).toBeVisible();
});

test("a passage is reviewed with the keyboard, timed, and the next opens", async ({
  page,
}) => {
  await asLearner(page, OWNER);
  const posted: { url: string; body: Record<string, unknown> }[] = [];
  let left = 2;
  const json = (body: unknown) => ({
    contentType: "application/json",
    body: JSON.stringify(body),
  });
  const base = {
    text: "bees",
    skill: "detail",
    checker_model: "baidu/ernie",
    note: null,
  };
  await page.route("**/api/backend/reading/review/**", async (route) => {
    const url = new URL(route.request().url());
    if (route.request().method() === "POST") {
      posted.push({ url: url.pathname, body: route.request().postDataJSON() });
      left -= 1;
      return route.fulfill(json({ id: "x", status: "approved" }));
    }
    if (url.pathname.endsWith("/reading/review/texts"))
      return route.fulfill(
        json({
          texts:
            left > 0
              ? [{ slug: "bees", title: "Honey bees", agreed: 1, flagged: 1 }]
              : [],
          stats: { decisions: 2 - left, median_seconds: null, overturned: 0 },
        }),
      );
    return route.fulfill(
      json({
        slug: "bees",
        title: "Honey bees",
        passage:
          "Honey bees live in large colonies.\n\nWorker bees collect nectar.",
        items: [
          {
            ...base,
            id: "bees-tfng-1",
            kind: "tfng",
            question: { statement: "Bees live alone." },
            key: "false",
            evidence: ["Honey bees live in large colonies."],
            checker_answer: "FALSE",
            agreed: true,
          },
          {
            ...base,
            id: "bees-mcq-1",
            kind: "mcq",
            question: {
              stem: "Who collects nectar?",
              options: ["Queens", "Workers", "Drones"],
            },
            key: 1,
            evidence: ["Worker bees collect nectar."],
            checker_answer: "A",
            agreed: false,
          },
        ],
      }),
    );
  });
  await page.goto("/duyet-doc");
  await page.getByRole("button", { name: /Honey bees/ }).click();
  const item = page.getByTestId("review-item");
  await expect(item.getByText("Bees live alone.")).toBeVisible();
  await expect(page.locator("mark")).toHaveText(
    "Honey bees live in large colonies.",
  );
  await expect(item.getByText("Máy kiểm tra không đồng ý")).toHaveCount(0);
  await page.keyboard.press("a");
  // The flagged question: the checker's answer is shown against the key.
  await expect(item.getByText("Who collects nectar?")).toBeVisible();
  await expect(item.getByText("Máy kiểm tra không đồng ý")).toBeVisible();
  await expect(item.locator(".en-feedback.is-wrong")).toHaveText(
    "Máy kiểm tra trả lời: A",
  );
  // Typing a note does not trigger shortcuts.
  await item.getByLabel(/Ghi chú/).fill("ra");
  await item.getByLabel(/Ghi chú/).blur();
  await page.keyboard.press("r");
  await page.keyboard.press("3");
  await page.keyboard.press("Enter");
  await expect(
    page.getByText("Không còn câu hỏi nào chờ duyệt."),
  ).toBeVisible();
  expect(posted.map((p) => p.url.split("/").pop())).toEqual([
    "bees-tfng-1",
    "bees-mcq-1",
  ]);
  expect(posted[0]!.body).toMatchObject({ decision: "approve" });
  expect(typeof posted[0]!.body.seconds).toBe("number");
  expect(posted[1]!.body).toMatchObject({
    decision: "reject",
    reason: "two_answers",
    note: "ra",
  });
});
