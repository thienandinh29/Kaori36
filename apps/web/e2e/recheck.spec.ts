import { expect, test } from "@playwright/test";

// FORGET-001: the delayed grammar re-check on the home page (specs/forget-001/spec.md). The rest of
// the page runs against the real API; only the re-check calls are mocked.
const LEARNER =
  process.env.E2E_LEARNER_ID ?? "00000000-0000-4000-8000-0000000e2e01";
const ID = "0b9d2f4e-1c2a-4d3b-8e5f-6a7b8c9d0e1f";

test("a due re-check is answered once, with the key shown when wrong", async ({
  page,
}) => {
  await page.addInitScript((value) => {
    localStorage.setItem("nodetrail_english_learner", value);
  }, LEARNER);
  const posted: unknown[] = [];
  await page.route("**/api/backend/rechecks/**", async (route) => {
    const url = new URL(route.request().url());
    const json = (body: unknown) =>
      route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    if (url.pathname.endsWith("/rechecks/next"))
      return json({
        question: {
          id: ID,
          node: "articles-basic",
          node_name_vi: "Mạo từ a/an",
          prompt: "I saw ___ elephant at the zoo.",
          options: ["a", "an", "the", "—"],
          draft: true,
        },
      });
    posted.push(route.request().postDataJSON());
    return json({ correct: false, key: "an" });
  });
  await page.goto("/");
  const card = page.getByTestId("recheck-card");
  await expect(card.getByText("Mạo từ a/an")).toBeVisible();
  await card.getByRole("button", { name: "a", exact: true }).click();
  await expect(card.getByRole("status")).toContainText("Chưa đúng.");
  await expect(card.getByRole("status")).toContainText("an");
  await expect(card.getByRole("button", { name: "the" })).toBeDisabled();
  expect(posted).toEqual([{ learner_id: LEARNER, answer: "a" }]);
});

test("no card when nothing is due (real API)", async ({ page }) => {
  await page.addInitScript((value) => {
    localStorage.setItem("nodetrail_english_learner", value);
  }, LEARNER);
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.getByTestId("recheck-card")).toHaveCount(0);
});
