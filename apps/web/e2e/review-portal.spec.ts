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

/** A tiny valid WAV: 0.5 s of silence at 8 kHz. */
function silentWav(): Buffer {
  const samples = 4000;
  const b = Buffer.alloc(44 + samples * 2);
  b.write("RIFF", 0);
  b.writeUInt32LE(36 + samples * 2, 4);
  b.write("WAVEfmt ", 8);
  b.writeUInt32LE(16, 16);
  b.writeUInt16LE(1, 20);
  b.writeUInt16LE(1, 22);
  b.writeUInt32LE(8000, 24);
  b.writeUInt32LE(16000, 28);
  b.writeUInt16LE(2, 32);
  b.writeUInt16LE(16, 34);
  b.write("data", 36);
  b.writeUInt32LE(samples * 2, 40);
  return b;
}

async function mockOne(
  page: Page,
  contentType: string,
  item: Record<string, unknown>,
  posted: unknown[],
) {
  let done = 0;
  await page.route("**/api/backend/review/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname.endsWith("/audio"))
      return route.fulfill({ contentType: "audio/wav", body: silentWav() });
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
          { id: BATCH, name: "Đợt", content_type: contentType, total: 1, done },
        ],
      });
    if (url.pathname.endsWith("/next"))
      return json({
        total: 1,
        done,
        unavailable: 0,
        item: done ? null : { content_type: contentType, ...item },
      });
    posted.push(request.postDataJSON());
    done = 1;
    return json({ content_id: item.content_id, value: "x" });
  });
  await page.goto(`/kiem-duyet#${TOKEN}`);
  await page.getByRole("button", { name: "Bắt đầu" }).click();
}

test("a grammar item is answered blind, then its key judged", async ({
  page,
}) => {
  const posted: unknown[] = [];
  await mockOne(
    page,
    "grammar_item",
    {
      content_id: "be-present-1",
      prompt: "My sister ___ a nurse.",
      options: ["are", "is", "am", "be"],
      key: 1,
    },
    posted,
  );
  const item = page.getByTestId("review-grammar");
  await expect(page.getByTestId("review-key")).toHaveCount(0);
  await item.getByRole("radio", { name: "B", exact: true }).click();
  await item.getByRole("button", { name: "Xem đáp án" }).click();
  await expect(page.getByTestId("review-key")).toHaveText("B. is");
  await item.getByRole("radio", { name: "Sai" }).click();
  await item.getByRole("combobox").selectOption("two_answers");
  await item.getByRole("button", { name: "Lưu và sang mục tiếp" }).click();
  await expect(page.getByText("Đã xong đợt này")).toBeVisible();
  expect(posted).toEqual([
    { answer: "B", verdict: "wrong", reason: "two_answers" },
  ]);
});

test("a vocabulary entry is judged with a reason", async ({ page }) => {
  const posted: unknown[] = [];
  await mockOne(
    page,
    "vocab_entry",
    {
      content_id: "important-adjective",
      lemma: "important",
      pos: "adjective",
      level: "A2",
      ipa: "/ɪmˈpɔːtənt/",
      definition: "having great value or a strong effect on something",
      vi: "quan trọng",
      examples: ["It is important to sleep well before an exam."],
      collocations: [],
      forms: ["Teachers often stress the importance of reading every day."],
    },
    posted,
  );
  const item = page.getByTestId("review-vocab");
  await expect(item.getByText("quan trọng")).toBeVisible();
  await item.getByRole("radio", { name: "Sai" }).click();
  await item.getByRole("combobox").selectOption("gloss");
  await item.getByRole("button", { name: "Lưu và sang mục tiếp" }).click();
  await expect(page.getByText("Đã xong đợt này")).toBeVisible();
  expect(posted).toEqual([{ verdict: "wrong", reason: "gloss" }]);
});

test("a sound is heard and judged, with no reason asked", async ({ page }) => {
  const posted: unknown[] = [];
  const id = "0b9d2f4e-1c2a-4d3b-8e5f-6a7b8c9d0e1f";
  await mockOne(
    page,
    "speech_target",
    {
      content_id: `${id}:0`,
      sentence: "I think the best part of the test was the last question.",
      word: "think",
      ipa: "θ",
      sound_vi: "Âm /θ/ (think, three)",
      start_ms: 100,
      end_ms: 180,
    },
    posted,
  );
  const item = page.getByTestId("review-speech");
  await expect(item.locator("audio")).toHaveAttribute("src", /^blob:/);
  await item.getByRole("button", { name: "Nghe đoạn có âm này" }).click();
  await item.getByRole("radio", { name: "Sai" }).click();
  await expect(item.getByRole("combobox")).toHaveCount(0);
  await item.getByRole("button", { name: "Lưu và sang mục tiếp" }).click();
  await expect(page.getByText("Đã xong đợt này")).toBeVisible();
  expect(posted).toEqual([{ verdict: "wrong" }]);
});
