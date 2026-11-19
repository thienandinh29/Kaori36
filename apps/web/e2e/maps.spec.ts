import { expect, test } from "@playwright/test";

// Two maps, M4: every IELTS competency with its foundations, from the real API.
const LEARNER =
  process.env.E2E_LEARNER_ID ?? "00000000-0000-4000-8000-0000000e2e01";

test("the skill map shows the four skills, statuses and proposed links", async ({
  page,
}) => {
  await page.addInitScript((value) => {
    localStorage.setItem("nodetrail_english_learner", value);
  }, LEARNER);
  await page.goto("/ban-do");
  const maps = page.getByTestId("two-maps");
  await expect(
    maps.getByRole("heading", { name: "Bản đồ kỹ năng" }),
  ).toBeVisible();
  for (const skill of ["Đọc", "Nghe", "Viết", "Nói"])
    await expect(
      maps.getByRole("heading", { name: skill, exact: true }),
    ).toBeVisible();
  const reading = maps.getByTestId("comp-reading-detail");
  await expect(
    reading.getByText("NodeTrail chưa có bài luyện", { exact: false }),
  ).toBeVisible();
  const grammar = maps.getByTestId("comp-writing-grammar");
  await expect(
    grammar.getByText("chưa có trong khóa học").first(),
  ).toBeVisible();
  // Not-live foundations still show their Vietnamese names (the image carries the proposed path).
  await expect(grammar.getByText("agreement-long-subjects")).toHaveCount(0);
  const link = grammar.getByRole("link", { name: /Mạo từ/ }).first();
  await expect(link).toHaveAttribute("href", /^\/on-tap\//);
  await expect(maps.getByText("đề xuất", { exact: false })).toBeVisible();
});
