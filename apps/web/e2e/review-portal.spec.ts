import { expect, test, type Page, type Route } from "@playwright/test";

// The reviewer portal (specs/validation/step-v2.md). The flow runs on mocked portal calls in the
// browser; the refusal of a forged link runs against the real API.
const TOKEN = "T".repeat(43);
const BATCH = "0b9d2f4e-1c2a-4d3b-8e5f-6a7b8c9d0e1f";
const PASSAGE = "Honey bees live in colonies. A colony has one queen.";

async function mockPortal(page: Page, posted: unknown[], headers: string[]) {
  let done = 0;
  await page.route("**/api/backend/review/**", async (route: Route) => {
    const request = route.request();
    headers.push(request.headers()["x-reviewer-token"] ?? "");
    const url = new URL(request.url());
    const json = (body: unknown) =>
      route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(body),
      });
    if (url.pathname.endsWith("/review/me"))
      return json({
        name: "Cô Lan",
        role: "expert_teacher",
        batches: [
          {
            id: BATCH,
            name: "Đọc đợt 1",
            content_type: "reading_item",
            total: 1,
            done,
          },
        ],
      });
    if (url.pathname.endsWith("/next"))
      return json({
        total: 1,
        done,
        unavailable: 0,
        item:
          done > 0
            ? null
            : {
                content_type: "reading_item",
                content_id: "bees-tfng-1",
                kind: "tfng",
                skill: "detail",
                passage: PASSAGE,
                question: {
                  kind: "tfng",
                  skill: "detail",
                  statement: "A colony has two queens.",
                },
                key: "false",
              },
      });
    posted.push(request.postDataJSON());
    done = 1;
    return json({ content_id: "bees-tfng-1", value: "right" });
  });
}

test("a reviewer answers blind, then judges the key", async ({ page }) => {
  const posted: unknown[] = [];
  const headers: string[] = [];
  await mockPortal(page, posted, headers);
  await page.goto(`/kiem-duyet#${TOKEN}`);
  const card = page.getByTestId("review-portal");
  await expect(card.getByText("Xin chào Cô Lan.")).toBeVisible();
  // The token leaves the address bar at once.
  await expect(page).toHaveURL(/\/kiem-duyet$/);
  await card.getByRole("button", { name: "Bắt đầu" }).click();
  const item = page.getByTestId("review-item");
  await expect(item.getByText(PASSAGE)).toBeVisible();
  // Step 1: the key is hidden until the reviewer has answered.
  await expect(page.getByTestId("review-key")).toHaveCount(0);
  const reveal = item.getByRole("button", { name: "Xem đáp án" });
  await expect(reveal).toBeDisabled();
  await item.getByRole("radio", { name: "FALSE" }).click();
  await reveal.click();
  await expect(page.getByTestId("review-key")).toHaveText("FALSE");
  await item.getByRole("radio", { name: "Đúng" }).click();
  await item.getByRole("button", { name: "Lưu và sang mục tiếp" }).click();
  await expect(
    card.getByText("Đã xong đợt này. Cảm ơn thầy/cô!"),
  ).toBeVisible();
  expect(posted).toEqual([{ answer: "FALSE", verdict: "right" }]);
  expect(new Set(headers)).toEqual(new Set([TOKEN]));
});

test("a forged link is refused by the real API", async ({ page }) => {
  await page.goto(`/kiem-duyet#${"x".repeat(43)}`);
  await expect(
    page.getByText("Đường link không hợp lệ", { exact: false }),
  ).toBeVisible();
});

test("a page without a link explains what to do", async ({ page }) => {
  await page.goto("/kiem-duyet");
  await expect(
    page.getByText("Đường link không hợp lệ", { exact: false }),
  ).toBeVisible();
});

test("a batch whose texts are not ready is not called finished", async ({
  page,
}) => {
  await page.route("**/api/backend/review/**", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(
        route.request().url().endsWith("/review/me")
          ? {
              name: "Cô Lan",
              role: "expert_teacher",
              batches: [
                {
                  id: BATCH,
                  name: "Đọc đợt 1",
                  content_type: "reading_item",
                  total: 4,
                  done: 0,
                },
              ],
            }
          : { total: 4, done: 0, unavailable: 4, item: null },
      ),
    }),
  );
  await page.goto(`/kiem-duyet#${TOKEN}`);
  await page.getByRole("button", { name: "Bắt đầu" }).click();
  await expect(
    page.getByText("Hiện chưa có mục nào xem được", { exact: false }),
  ).toBeVisible();
  await expect(page.getByText("Đã xong đợt này")).toHaveCount(0);
});
