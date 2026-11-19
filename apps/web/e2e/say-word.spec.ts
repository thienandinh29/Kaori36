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
          {
            phone: "tʃ",
            gop: -0.2,
            closeness: 94,
            heard: null,
            dropped: false,
            how: "như ch",
          },
          {
            phone: "uː",
            gop: -4.0,
            closeness: 26,
            heard: "ʊ",
            dropped: false,
            how: "u dài: chu tròn môi",
          },
          {
            phone: "z",
            gop: -7.0,
            closeness: 10,
            heard: "s",
            dropped: true,
            how: "rung dây thanh",
          },
        ],
        heard: ["tʃ", "ʊ"],
        guide: [
          {
            index: 1,
            phone: "uː",
            times: 2,
            of: 3,
            heard: "ʊ",
            dropped: false,
            how: "u dài: chu tròn môi",
            change: "Chu môi tròn hơn và giữ âm lâu hơn.",
            minimal: ["pool", "pull"],
          },
        ],
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
  // The word's IPA, each sound coloured; a tap shows the score, what was heard and how to say it.
  const phones = result.locator(".nt-ipa-phone");
  await expect(phones).toHaveText(["tʃ", "uː", "z"]);
  await expect(phones.nth(2)).toHaveClass(/is-dropped/);
  await phones.nth(1).click();
  const detail = result.getByTestId("phone-detail");
  await expect(detail).toContainText("26/100");
  await expect(detail).toContainText("nghe giống /ʊ/");
  await expect(detail).toContainText("chu tròn môi");
  // The same sound low twice in the last three tries: a guide with a pair to hear.
  const guide = result.getByTestId("say-guide");
  await expect(guide).toContainText("Âm /uː/ chưa chuẩn 2/3 lần gần đây");
  await expect(guide).toContainText("pool");
  await expect(guide).toContainText("bản nháp");
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
