import { expect, test, type Page } from "@playwright/test";

// Shadowing (specs/listening-reading/step-4.4d.md). Chromium's fake microphone plays a tone; a
// stand-in for YouTube's player script records what the page asks of it (no network to YouTube).
const LEARNER =
  process.env.E2E_LEARNER_ID ?? "00000000-0000-4000-8000-0000000e2e01";

test.use({
  permissions: ["microphone"],
  launchOptions: {
    args: [
      "--use-fake-device-for-media-stream",
      "--use-fake-ui-for-media-stream",
    ],
  },
});

async function asLearner(page: Page) {
  await page.addInitScript((value) => {
    localStorage.setItem("nodetrail_english_learner", value);
  }, LEARNER);
}

/** A second of a 440 Hz tone at 8 kHz: a valid WAV the browser decodes. */
function toneWav(): Buffer {
  const rate = 8000;
  const n = rate;
  const b = Buffer.alloc(44 + n * 2);
  b.write("RIFF", 0);
  b.writeUInt32LE(36 + n * 2, 4);
  b.write("WAVEfmt ", 8);
  b.writeUInt32LE(16, 16);
  b.writeUInt16LE(1, 20);
  b.writeUInt16LE(1, 22);
  b.writeUInt32LE(rate, 24);
  b.writeUInt32LE(rate * 2, 28);
  b.writeUInt16LE(2, 32);
  b.writeUInt16LE(16, 34);
  b.write("data", 36);
  b.writeUInt32LE(n * 2, 40);
  for (let i = 0; i < n; i++)
    b.writeInt16LE(
      Math.round(12000 * Math.sin((2 * Math.PI * 440 * i) / rate)),
      44 + i * 2,
    );
  return b;
}

test("a learner shadows a bank sentence and hears their own take (never uploaded)", async ({
  page,
}) => {
  await asLearner(page);
  const uploads: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST") uploads.push(r.url());
  });
  await page.route("**/api/backend/shadowing/**", (route) => {
    const url = new URL(route.request().url());
    const json = (b: unknown) =>
      route.fulfill({
        contentType: "application/json",
        body: JSON.stringify(b),
      });
    if (url.pathname.endsWith("/shadowing/texts"))
      return json({
        available: true,
        texts: [{ slug: "bees", title: "Honey bees", sentences: 2 }],
      });
    return json({
      slug: "bees",
      title: "Honey bees",
      sentences: [
        { id: "bees-shadow-1", text: "Bees fly to flowers every day." },
        { id: "bees-shadow-2", text: "They carry pollen back to the hive." },
      ],
    });
  });
  await page.route("**/api/backend/listening/items/*/audio*", (route) =>
    route.fulfill({ contentType: "audio/wav", body: toneWav() }),
  );
  await page.goto("/noi-duoi");
  const s = page.getByTestId("shadowing-sentence");
  await expect(s).toContainText("Câu 1/2");
  await expect(s).toContainText("Bees fly to flowers every day.");
  await s.getByRole("button", { name: "Nghe mẫu" }).click();
  await s.getByRole("button", { name: "Ghi âm" }).click();
  await expect(s.getByRole("status").first()).toContainText("Đang ghi");
  await page.waitForTimeout(1500);
  await s.getByRole("button", { name: "Dừng" }).click();
  const take = page.getByTestId("shadowing-take");
  await expect(take).toContainText("giây");
  await expect(take.locator("audio")).toHaveCount(1);
  await expect(take).toContainText("không đánh giá đúng sai");
  await s.getByRole("button", { name: "Câu sau" }).click();
  await expect(s).toContainText("They carry pollen back to the hive.");
  await expect(page.getByTestId("shadowing-take")).toHaveCount(0);
  expect(uploads).toEqual([]); // the recording never leaves the browser
});

test("a YouTube link opens the official player with loop and speed", async ({
  page,
}) => {
  await asLearner(page);
  await page.route("**/api/backend/shadowing/texts*", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ available: false, texts: [] }),
    }),
  );
  await page.route("https://www.youtube.com/iframe_api", (route) =>
    route.fulfill({
      contentType: "text/javascript",
      body: `
        window.ytCalls = [];
        let t = 3;
        window.YT = { Player: function (el, o) {
          window.ytCalls.push(["new", o.host, o.videoId]);
          return {
            getCurrentTime: () => (t += 4),
            seekTo: (s) => window.ytCalls.push(["seek", s]),
            playVideo: () => window.ytCalls.push(["play"]),
            setPlaybackRate: (r) => window.ytCalls.push(["rate", r]),
            destroy: () => {},
          };
        } };
        window.onYouTubeIframeAPIReady();`,
    }),
  );
  await page.goto("/noi-duoi");
  await expect(
    page.getByText("Chưa bật giọng đọc", { exact: false }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Video YouTube" }).click();
  const v = page.getByTestId("shadowing-video");
  await v
    .getByLabel("Link YouTube:")
    .fill("https://evil.example/watch?v=dQw4w9WgXcQ");
  await v.getByRole("button", { name: "Mở video" }).click();
  await expect(v).toContainText("Không đọc được link này");
  await v.getByLabel("Link YouTube:").fill("https://youtu.be/dQw4w9WgXcQ?si=x");
  await v.getByRole("button", { name: "Mở video" }).click();
  await expect(page.getByTestId("shadowing-player")).toBeVisible();
  await v.getByRole("button", { name: "Đặt điểm A" }).click();
  await v.getByRole("button", { name: "Đặt điểm B" }).click();
  await expect(v).toContainText("Đoạn lặp: 0:07 – 0:11");
  await v.getByRole("button", { name: "Lặp A–B" }).click();
  await v.getByRole("button", { name: "0.75×" }).click();
  const calls = await page.evaluate(
    () => (window as unknown as { ytCalls: unknown[] }).ytCalls,
  );
  expect(calls).toEqual([
    ["new", "https://www.youtube-nocookie.com", "dQw4w9WgXcQ"],
    ["seek", 7],
    ["play"],
    ["rate", 0.75],
  ]);
});
