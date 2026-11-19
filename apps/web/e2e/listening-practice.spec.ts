import { expect, test, type Page } from "@playwright/test";

// Listening from the Reading bank, CP5a (specs/listening-reading/step-4.4b.md).
const LEARNER =
  process.env.E2E_LEARNER_ID ?? "00000000-0000-4000-8000-0000000e2e01";

async function asLearner(page: Page) {
  await page.addInitScript((value) => {
    localStorage.setItem("nodetrail_english_learner", value);
  }, LEARNER);
}

/** A tenth of a second of silence: a valid WAV the browser can play. */
function silentWav(): Buffer {
  const rate = 8000;
  const samples = rate / 10;
  const b = Buffer.alloc(44 + samples * 2);
  b.write("RIFF", 0);
  b.writeUInt32LE(36 + samples * 2, 4);
  b.write("WAVEfmt ", 8);
  b.writeUInt32LE(16, 16);
  b.writeUInt16LE(1, 20);
  b.writeUInt16LE(1, 22);
  b.writeUInt32LE(rate, 24);
  b.writeUInt32LE(rate * 2, 28);
  b.writeUInt16LE(2, 32);
  b.writeUInt16LE(16, 34);
  b.write("data", 36);
  b.writeUInt32LE(samples * 2, 40);
  return b;
}

test("without the server voice, the page says how to turn it on (real API)", async ({
  page,
}) => {
  await asLearner(page);
  await page.goto("/nghe");
  await expect(
    page.getByText("Chưa bật giọng đọc của máy chủ", { exact: false }),
  ).toBeVisible();
});

test("a learner hears a sentence, writes it and sees each word marked", async ({
  page,
}) => {
  await asLearner(page);
  const posted: unknown[] = [];
  const heard: string[] = [];
  const trace = {
    kind: "bkt_update",
    concept_slug: "listening-dictation",
    at: "2026-11-20T09:00:00Z",
    prior: 0.2,
    posterior: 0.1,
    evidence: {},
    rule: "listening.answer",
    rule_vi: "Nghe chép chính tả: chưa đúng",
    alternatives: [],
  };
  await page.route("**/api/backend/listening/**", async (route) => {
    const url = new URL(route.request().url());
    const json = (b: unknown) =>
      route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(b),
      });
    if (url.pathname.endsWith("/audio")) {
      heard.push(
        `${url.pathname.split("/").at(-2)}:${url.searchParams.get("pace")}`,
      );
      return route.fulfill({ contentType: "audio/wav", body: silentWav() });
    }
    if (url.pathname.endsWith("/listening/texts"))
      return json({
        available: true,
        texts: [{ slug: "bees", title: "Honey bees", dictation: 1, gaps: 1 }],
      });
    if (url.pathname.endsWith("/listening/texts/bees"))
      return json({
        slug: "bees",
        title: "Honey bees",
        items: [
          { id: "bees-dictation-1", kind: "dictation", prompt: null },
          { id: "bees-gap-1", kind: "gap", prompt: "Worker bees ___ nectar." },
        ],
      });
    posted.push(route.request().postDataJSON());
    return json(
      posted.length === 1
        ? {
            correct: false,
            score: 0.8,
            key: "Honey bees live in hives.",
            sentence: "Honey bees live in hives.",
            words: [
              { word: "honey", status: "right" },
              { word: "bees", status: "right" },
              { word: "live", status: "right" },
              { word: "in", status: "right" },
              { word: "hives", status: "missed" },
            ],
            competency: "listening-dictation",
            trace,
          }
        : {
            correct: true,
            score: 1,
            key: "collect",
            sentence: "Worker bees collect nectar.",
            words: [],
            competency: "listening-detail",
            trace,
          },
    );
  });
  await page.goto("/nghe");
  await page.getByRole("link", { name: "Honey bees" }).click();
  const item = page.getByTestId("listening-item");
  await expect(item).toContainText("Nghe và chép lại cả câu");
  // Nothing of the sentence is on the page before answering.
  await expect(page.getByText("Honey bees live")).toHaveCount(0);
  await item.getByRole("button", { name: "Nghe", exact: true }).click();
  await expect(item).toContainText("Còn 2 lượt nghe");
  await item.getByRole("button", { name: "Nghe chậm" }).click();
  await expect(item).toContainText("Còn 1 lượt nghe");
  expect(heard).toEqual(["bees-dictation-1:normal", "bees-dictation-1:slow"]);
  await item.getByLabel("Câu bạn nghe được:").fill("Honey bees live in");
  await item.getByRole("button", { name: "Kiểm tra" }).click();
  const result = page.getByTestId("listening-result");
  await expect(result).toContainText("Chưa đúng.");
  await expect(result).toContainText("Đúng 80% số từ.");
  await expect(result.locator(".nt-word.is-missed")).toHaveText("hives");
  await expect(result).toContainText("Honey bees live in hives.");
  await result.getByRole("button", { name: "Câu tiếp" }).click();
  await expect(page.getByTestId("listening-prompt")).toHaveText(
    "Worker bees ___ nectar.",
  );
  await item.getByLabel("Từ còn thiếu:").fill("collect");
  await item.getByRole("button", { name: "Kiểm tra" }).click();
  await expect(result).toContainText("Đúng.");
  await expect(result).toContainText("collect");
  expect(posted).toEqual([
    { learner_id: LEARNER, answer: "Honey bees live in" },
    { learner_id: LEARNER, answer: "collect" },
  ]);
  await result.getByRole("button", { name: "Xong" }).click();
  await expect(page.getByText("Bạn đã làm hết bài nghe")).toBeVisible();
});
