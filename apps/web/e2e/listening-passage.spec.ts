import { expect, test, type Page } from "@playwright/test";

// Listening to a whole Reading passage, CP5b (specs/listening-reading/step-4.4c.md). The API is
// stood in for here: CI runs without the server voice.
const LEARNER =
  process.env.E2E_LEARNER_ID ?? "00000000-0000-4000-8000-0000000e2e01";

async function asLearner(page: Page) {
  await page.addInitScript((value) => {
    localStorage.setItem("nodetrail_english_learner", value);
  }, LEARNER);
}

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

test("a learner hears the whole passage, answers, and only then reads it", async ({
  page,
}) => {
  await asLearner(page);
  const parts: string[] = [];
  const sent: unknown[] = [];
  await page.route("**/api/backend/listening/**", async (route) => {
    const url = new URL(route.request().url());
    const json = (b: unknown) =>
      route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(b),
      });
    if (url.pathname.endsWith("/listening/texts"))
      return json({ available: true, texts: [] });
    if (url.pathname.endsWith("/listening/passages"))
      return json({
        available: true,
        texts: [
          {
            slug: "bees",
            title: "Honey bees",
            questions: 2,
            parts: 3,
            read_before: true,
          },
        ],
      });
    if (url.pathname.includes("/audio/")) {
      parts.push(url.pathname.split("/").pop()!);
      return route.fulfill({ contentType: "audio/wav", body: silentWav() });
    }
    if (url.pathname.endsWith("/submit")) {
      sent.push(route.request().postDataJSON());
      return json({
        slug: "bees", correct: 1, total: 2, answered: 1,
        items: [
          { id: "bees-tfng-1", answer: "TRUE", correct: true, key: "TRUE", evidence: ["x"] },
          { id: "bees-mcq-1", answer: null, correct: false, key: "A. Stored honey", evidence: ["y"] },
        ],
        transcript: "Honey bees live in large colonies.\n\nIn winter the bees stay together.",
      }); // prettier-ignore
    }
    return json({
      slug: "bees", title: "Honey bees", parts: 3,
      items: [
        { id: "bees-tfng-1", kind: "tfng", skill: "detail", statement: "A colony can hold sixty thousand bees." },
        { id: "bees-mcq-1", kind: "mcq", skill: "detail", stem: "What do bees eat in winter?",
          options: ["Stored honey", "Nectar", "Pollen", "Leaves"] },
      ],
    }); // prettier-ignore
  });
  await page.goto("/nghe");
  const list = page.getByTestId("listening-passages");
  await expect(list).toContainText("bạn đã đọc bài này");
  await list.getByRole("link", { name: "Honey bees" }).click();
  const box = page.getByTestId("listening-passage");
  await expect(box).not.toContainText("large colonies"); // the passage is not on the page yet
  await box.getByRole("button", { name: "Nghe bài" }).click();
  await expect.poll(() => parts).toEqual(["0", "1", "2"]); // every part, in order
  await expect(
    box.getByRole("button", { name: /Nghe lại \(còn 1 lần\)/ }),
  ).toBeVisible();
  await box.getByRole("radio", { name: "TRUE" }).click();
  await box.getByRole("button", { name: "Nộp bài" }).click();
  await expect(page.getByTestId("passage-score")).toContainText("Đúng 1/2 câu");
  await expect(box).toContainText("A. Stored honey");
  await expect(box).toContainText("large colonies"); // shown only after answering
  expect(sent).toEqual([
    { learner_id: LEARNER, answers: { "bees-tfng-1": "TRUE" } },
  ]);
});
