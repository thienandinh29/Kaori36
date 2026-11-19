import { expect, test } from "@playwright/test";

// Saying a vocabulary word (specs/pronunciation/step-3.7.md). Chromium's fake microphone; the
// analysis is mocked (the pronunciation service is a heavy profile CI does not start).
test.use({
  permissions: ["microphone"],
  launchOptions: {
    args: [
      "--use-fake-device-for-media-stream",
      "--use-fake-ui-for-media-stream",
    ],
  },
});

test("a learner says a word, hears it back, and the owner sees each sound", async ({
  page,
}) => {
  await page.addInitScript(() => {
    localStorage.removeItem("nodetrail_english_learner");
    localStorage.removeItem("nodetrail_say_consent");
  });
  const sent: string[] = [];
  await page.route("**/api/backend/vocab/say/status*", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        analysis: true,
        owner: true,
        consent: "voice-v1",
      }),
    }),
  );
  await page.route("**/api/backend/vocab/say?*", async (route) => {
    const url = new URL(route.request().url());
    sent.push(
      `${url.searchParams.get("word")}|${url.searchParams.get("consent")}`,
    );
    expect(route.request().headers()["content-type"]).toBe("audio/wav");
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        problems: [],
        phones: [
          { phone: "tʃ", gop: -0.2, heard: null, dropped: false },
          { phone: "uː", gop: -4.0, heard: "ʊ", dropped: false },
          { phone: "z", gop: -7.0, heard: "s", dropped: true },
        ],
        heard: ["tʃ", "ʊ"],
      }),
    });
  });
  await page.goto("/tu-vung");
  const card = page.getByTestId("flashcard");
  await card.getByRole("button", { name: "Lật thẻ" }).click();
  const say = card.getByTestId("say-word");
  await say.getByRole("button", { name: "Nói từ này" }).click();
  await expect(say).toContainText("Đang ghi");
  await page.waitForTimeout(1200);
  await say.getByRole("button", { name: "Dừng" }).click();
  await expect(say.locator("audio")).toHaveCount(1);
  // Consent first, then the analysis.
  await say.getByRole("button", { name: "Tôi đồng ý" }).click();
  await say.getByRole("button", { name: "Phân tích từng âm" }).click();
  const result = say.getByTestId("say-result");
  await expect(result).toContainText("bỏ mất âm");
  await expect(result).toContainText("nghe giống ʊ");
  await expect(result).toContainText("chưa phải điểm đúng sai");
  expect(sent).toHaveLength(1);
  expect(sent[0]).toMatch(/^[a-z' -]+:[a-z]+\|voice-v1$/);
});

test("without the analysis, saying a word is compared by ear only", async ({
  page,
}) => {
  await page.addInitScript(() =>
    localStorage.removeItem("nodetrail_english_learner"),
  );
  await page.goto("/tu-vung"); // the real API: a new learner is not the owner
  const card = page.getByTestId("flashcard");
  await card.getByRole("button", { name: "Lật thẻ" }).click();
  const say = card.getByTestId("say-word");
  await say.getByRole("button", { name: "Nói từ này" }).click();
  await page.waitForTimeout(1000);
  await say.getByRole("button", { name: "Dừng" }).click();
  await expect(say).toContainText("Bản ghi chỉ nằm trong trình duyệt");
  await expect(
    say.getByRole("button", { name: "Phân tích từng âm" }),
  ).toHaveCount(0);
});
