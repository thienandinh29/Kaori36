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
  // The graph is the default view; the list stays one tap away (and for screen readers).
  await expect(page.getByTestId("skill-graph")).toBeVisible();
  await maps.getByRole("tab", { name: "Dạng danh sách" }).click();
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

test("the graph view links skills to foundations and explains a node", async ({
  page,
}) => {
  await page.addInitScript((value) => {
    localStorage.setItem("nodetrail_english_learner", value);
  }, LEARNER);
  await page.goto("/ban-do");
  const graph = page.getByTestId("skill-graph");
  await expect(graph.locator(".nt-gnode.is-competency").first()).toBeVisible();
  // Reading is shown first; "Tất cả" shows every skill.
  await graph.getByRole("button", { name: "Tất cả" }).click();
  await expect(
    graph.getByText("Viết Task 1", { exact: false }).first(),
  ).toBeVisible();
  await graph.getByRole("button", { name: "Đọc", exact: true }).click();
  const comps = graph.locator(".nt-gnode.is-competency strong");
  await expect(comps.first()).toBeVisible();
  for (const name of await comps.allInnerTexts())
    expect(name.startsWith("Đọc")).toBe(true);
  await expect(graph.locator(".react-flow__edge").first()).toBeAttached();
  await graph.getByText("Đọc: tìm thông tin chi tiết").click();
  const panel = page.getByTestId("graph-panel");
  await expect(panel).toContainText("Đọc: tìm thông tin chi tiết");
  await expect(panel).toContainText("Cần");
  await expect(panel.getByRole("link", { name: "Luyện ngay" })).toHaveAttribute(
    "href",
    "/doc",
  );
  // Following a link in the panel moves to that foundation.
  await panel.locator("button.en-link").first().click();
  await expect(panel).toContainText(/Cần cho|Giúp/);
});
