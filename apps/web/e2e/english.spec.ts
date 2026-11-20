import { expect, test, type Page } from "@playwright/test";
import { answerKeys } from "./keys";

// A learner the stack serves draft items to (DRAFT_ITEM_LEARNERS); CI creates it.
const LEARNER =
  process.env.E2E_LEARNER_ID ?? "00000000-0000-4000-8000-0000000e2e01";
const KEYS = answerKeys();

async function asLearner(page: Page, id: string | null) {
  await page.addInitScript((value) => {
    if (value) localStorage.setItem("nodetrail_english_learner", value);
    else localStorage.removeItem("nodetrail_english_learner");
  }, id);
}

async function currentItem(page: Page): Promise<string> {
  const id = await page.locator("[data-item-id]").getAttribute("data-item-id");
  if (!id) throw new Error("no question on the page");
  return id;
}

/** Chooses the right option, or a wrong one, from the item bank's key. */
async function answer(page: Page, right: boolean) {
  const id = await currentItem(page);
  const key = KEYS.get(id);
  expect(key, `answer key for ${id}`).toBeTruthy();
  const options = page.getByRole("radio");
  const texts = await options.allInnerTexts();
  const index = texts.findIndex(
    (t) => (t.split("\n").at(-1)?.trim() === key) === right,
  );
  await options.nth(index).click();
  await page.getByRole("button", { name: "Gửi" }).click();
}

test("the level test ends with an estimated level, never presented as a score", async ({
  page,
}) => {
  await asLearner(page, LEARNER);
  await page.goto("/kiem-tra");
  await page.getByRole("button", { name: "Bắt đầu" }).click();
  const result = page.getByText("Kết quả ước lượng");
  for (let i = 0; i < 40; i++) {
    await expect(page.locator("[data-item-id]").or(result)).toBeVisible();
    if (await result.isVisible()) break;
    const id = await currentItem(page);
    if (KEYS.has(id)) {
      // grammar: drafts are labelled
      await expect(page.getByText("Bản nháp", { exact: true })).toBeVisible();
      await answer(page, true);
    } else {
      await page.getByRole("radio").first().click(); // the vocabulary part
      await page.getByRole("button", { name: "Gửi" }).click();
    }
    // wait for a different question, or the result
    await expect(
      page.locator(`[data-item-id]:not([data-item-id="${id}"])`).or(result),
    ).toBeVisible();
  }
  await expect(result).toBeVisible();
  await expect(
    page.getByText("ước lượng, không phải điểm IELTS"),
  ).toBeVisible();
  await page.getByRole("link", { name: "Xem lộ trình của bạn" }).click();
  await expect(
    page.getByRole("heading", { name: "Lộ trình của bạn" }),
  ).toBeVisible();
});

test("a failed milestone test explains each mistake and opens quick checks", async ({
  page,
}) => {
  await asLearner(page, LEARNER);
  await page.goto("/on-tap/cot-moc/conditional-3");
  await page.getByRole("button", { name: "Bắt đầu" }).click();
  for (let i = 0; i < 3; i++) {
    await answer(page, false);
    await expect(page.getByText("Chưa đúng.")).toBeVisible();
    await expect(page.getByText("Đáp án đúng")).toBeVisible();
    if (i < 2)
      await page.getByRole("button", { name: "Câu tiếp theo" }).click();
  }
  await expect(page.getByText("Chưa qua cột mốc")).toBeVisible();
  await page.getByRole("button", { name: "Câu tiếp theo" }).click();
  await expect(page.getByText("Kiểm tra nhanh từng phần")).toBeVisible();
  for (
    let i = 0;
    i < 4 && (await page.locator("[data-item-id]").count());
    i++
  ) {
    await answer(page, false);
    const more = page.getByRole("button", { name: "Câu tiếp theo" });
    await expect(more.or(page.getByText("Nên luyện trước"))).toBeVisible();
    if (await more.isVisible()) await more.click();
    else break;
  }
  await expect(page.getByText("Nên luyện trước")).toBeVisible();
  await expect(page.getByRole("link", { name: "Luyện ngay" })).toBeVisible();
});

test("new words are flashcards first, then typed from memory", async ({
  page,
}) => {
  await asLearner(page, null); // a fresh learner: vocabulary needs no draft permission
  await page.goto("/tu-vung");
  const card = page.getByTestId("flashcard");
  await expect(card).toBeVisible();
  // Step 1: every new word as a card; the back shows the meaning.
  const lemmas: string[] = [];
  for (;;) {
    lemmas.push(
      (await card.locator(".nt-card-front strong").innerText()).trim(),
    );
    // The front already shows the Vietnamese meaning and an example containing the word.
    await expect(card.locator(".nt-card-vi")).not.toBeEmpty();
    await expect(card.locator(".nt-card-example")).not.toBeEmpty();
    await card.getByRole("button", { name: "Lật thẻ" }).click();
    await expect(card.locator(".en-word")).toBeVisible();
    const start = card.getByRole("button", {
      name: "Đã xem hết, bắt đầu viết từ",
    });
    if (await start.count()) {
      await start.click();
      break;
    }
    await card.getByRole("button", { name: "Thẻ tiếp" }).click();
  }
  expect(lemmas.length).toBeGreaterThan(1);
  // Step 2: type each word from its meaning; a miss comes back at the end, as a retry.
  const write = async (word: string) => {
    await page.getByLabel("Gõ câu trả lời").fill(word);
    await page.getByRole("button", { name: "Gửi" }).click();
  };
  await write(lemmas[0]);
  await expect(page.getByText("Đúng rồi.")).toBeVisible();
  await expect(page.getByText("Ôn lại vào")).toBeVisible(); // the first try is scheduled
  await page.getByRole("button", { name: "Tiếp" }).click();
  await write("definitely-wrong");
  await expect(page.getByText("Chưa đúng.")).toBeVisible();
  await page.getByRole("button", { name: "Tiếp" }).click();
  for (const word of lemmas.slice(2)) {
    await write(word);
    await expect(page.getByText("Đúng rồi.")).toBeVisible();
    await page.getByRole("button", { name: "Tiếp" }).click();
  }
  await expect(
    page.getByText("Viết lại từ này", { exact: false }),
  ).toBeVisible();
  await write(lemmas[1]);
  await expect(page.getByText("Đúng rồi.")).toBeVisible();
  await expect(page.getByText("Ôn lại vào")).not.toBeVisible(); // a retry is not scheduled
  await page.getByRole("button", { name: "Tiếp" }).click();
  await expect(
    page.getByText(`đúng ngay lần đầu ${lemmas.length - 1}/${lemmas.length}`, {
      exact: false,
    }),
  ).toBeVisible();
});

test("an essay is written, measured by the worker, and deleted", async ({
  page,
}) => {
  await asLearner(page, LEARNER); // the starter prompts are drafts
  await page.goto("/viet");
  await expect(page.getByRole("heading", { name: "Luyện viết" })).toBeVisible();
  await page.locator('a[href="/viet/t2-plastic-ban"]').click();
  const essay =
    "Plastic bags is cheap. However, they pollute rivers. Paper bags is expensive.\n\nIn conclusion, a ban is sensible.";
  await page.getByRole("textbox").fill(essay);
  await expect(page.getByTestId("word-count")).toContainText("18 từ");
  await expect(page.getByTestId("word-count")).toContainText("cần ít nhất 250");
  const send = page.getByRole("button", { name: "Gửi bài" });
  await expect(send).toBeDisabled(); // the notice comes first
  await page.getByLabel("Tôi đã đọc và đồng ý").check();
  await send.click();
  await expect(page.getByRole("heading", { name: "Đã phân tích" })).toBeVisible(
    {
      timeout: 30_000,
    },
  );
  const result = page.getByTestId("essay-result");
  await expect(result).toContainText("18 / 250");
  await expect(result).toContainText("không phải điểm IELTS");
  await expect(result).toContainText("Đối lập");
  await expect(result).toContainText("Kết luận");
  if (process.env.LANGUAGETOOL_URL) {
    // the grammar check (specs/writing/step-2.2.md): this learner may see the draft error map
    // "Sửa trước" (step 2.6): the repeated error is one item; the style can be switched.
    const fix = page.getByTestId("fix-first");
    await expect(fix.locator('[data-kind="pattern"]')).toContainText(
      "lặp 2 lần",
    );
    await fix.getByRole("button", { name: "Tôi tự sửa" }).click();
    await expect(fix.locator('[data-kind="pattern"]')).not.toContainText(
      "Gợi ý sửa",
    );
    await fix.getByRole("button", { name: "Xem cách sửa" }).click();
    await expect(fix.locator('[data-kind="pattern"]')).toContainText("are");
    await fix.getByRole("button", { name: "Xem luôn cách sửa" }).click();
    // the full list is folded until the learner opens it
    const grammar = page.getByTestId("essay-grammar");
    await expect(grammar.locator("ul.en-issues")).toBeHidden();
    await grammar.getByText(/Tất cả lỗi ngữ pháp \(\d+\)/).click();
    await expect(
      grammar.locator('[data-errant-type="R:VERB:SVA"]').first(),
    ).toContainText("are");
    await expect(
      grammar.getByRole("link", { name: /Đã ghi vào lộ trình/ }).first(),
    ).toBeVisible();
    // hint first: the learner fixes the sentence themselves (step 2.4)
    await grammar
      .getByRole("button", { name: "Tự sửa câu này" })
      .first()
      .click();
    await page.getByLabel("Câu bạn sửa").fill("Plastic bags are cheap.");
    await page.getByRole("button", { name: "Kiểm tra" }).click();
    await expect(
      page.getByText("Đúng rồi! Bạn đã tự sửa được lỗi này."),
    ).toBeVisible();
  }
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Xóa bài viết" }).click();
  await expect(page.getByRole("heading", { name: "Luyện viết" })).toBeVisible();
});

test("repeated and memorised text is named first and not counted (step 2.7)", async ({
  page,
}) => {
  await asLearner(page, LEARNER);
  await page.goto("/viet/t2-plastic-ban");
  const part =
    "In this day and age, plastic bags pollute the rivers near our town every single week.";
  await page.getByRole("textbox").fill(`${part}\n\n${part}`);
  await page.getByLabel("Tôi đã đọc và đồng ý").check();
  await page.getByRole("button", { name: "Gửi bài" }).click();
  await expect(page.getByRole("heading", { name: "Đã phân tích" })).toBeVisible(
    { timeout: 30_000 },
  );
  const fix = page.getByTestId("fix-first");
  await expect(fix.locator("li").first()).toContainText(
    "Nhiều đoạn không phải lời của bạn",
  );
  await expect(page.getByTestId("own-words")).toContainText("/ 250");
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Xóa bài viết" }).click();
  await expect(page.getByRole("heading", { name: "Luyện viết" })).toBeVisible();
});

test("a Task 1 report is checked against its chart, with no band", async ({
  page,
}) => {
  await asLearner(page, LEARNER); // the chart prompts are drafts
  await page.goto("/viet/t1-internet-access");
  await expect(page.getByTestId("chart")).toBeVisible();
  await expect(page.getByTestId("chart").locator("svg")).toBeVisible();
  await page
    .getByRole("textbox")
    .fill(
      "The graph shows internet access. Overall, all three countries rose. Country A grew from 5% in 2000 to 85% in 2020, while Country B reached 90% in 2020.",
    );
  await page.getByLabel("Tôi đã đọc và đồng ý").check();
  await page.getByRole("button", { name: "Gửi bài" }).click();
  await expect(page.getByRole("heading", { name: "Đã phân tích" })).toBeVisible(
    {
      timeout: 30_000,
    },
  );
  const checks = page.getByTestId("task1-checks");
  await expect(checks.getByTestId("unsupported-number")).toHaveCount(1);
  await expect(checks.getByTestId("unsupported-number")).toContainText("90%");
  // the number not in the chart comes first in "Sửa trước" (step 2.6)
  await expect(
    page.getByTestId("fix-first").locator("li").first(),
  ).toContainText("90%");
  await expect(page.getByTestId("chart")).toBeVisible(); // the chart stays beside the result
  await expect(page.getByTestId("essay-band")).toHaveCount(0); // Task 1 never gets a band
  await expect(page.getByText("Chưa ước lượng band cho Task 1.")).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Xóa bài viết" }).click();
  await expect(page.getByRole("heading", { name: "Luyện viết" })).toBeVisible();
});

test("a lesson plays before practice: board, subtitles, a checkpoint, then practice", async ({
  page,
}) => {
  await asLearner(page, LEARNER); // the sample lesson is served to draft learners only
  await page.goto("/hoc/present-perfect-vs-past");
  const lesson = page.getByTestId("lesson");
  await expect(
    lesson.getByText("Bài mẫu để thử trình phát", { exact: false }),
  ).toBeVisible();
  await expect(
    lesson.getByRole("link", { name: "Tôi đã biết, làm luôn bài luyện" }),
  ).toHaveAttribute("href", "/on-tap/phan/present-perfect-vs-past");
  await lesson.getByRole("button", { name: "Bắt đầu bài học" }).click();
  // B1: both subtitles by default; the English one highlights the target form.
  await expect(lesson.locator(".nt-sub-en")).toBeVisible();
  await expect(lesson.locator(".nt-sub-vi")).toBeVisible();
  const next = lesson.getByRole("button", { name: "Tiếp", exact: true });
  // Step through with "Tiếp" (the voice may be absent in CI) until the timeline is on the board.
  for (
    let i = 0;
    i < 12 && !(await lesson.locator(".nt-board-timeline").count());
    i++
  )
    await next.click();
  await expect(lesson.locator(".nt-board-timeline")).toBeVisible();
  await expect(lesson.locator(".nt-example.is-spotlit")).toHaveCount(1);
  // On to the first checkpoint: "Tiếp" waits for an answer, which is graded and explained.
  for (
    let i = 0;
    i < 20 && !(await lesson.locator(".nt-checkpoint").count());
    i++
  )
    await next.click();
  await expect(next).toBeDisabled();
  await lesson.getByRole("button", { name: "No", exact: true }).click();
  await expect(lesson.getByText("Chưa đúng.")).toBeVisible();
  await expect(
    lesson.getByText("không tính vào mức độ nắm vững", { exact: false }),
  ).toBeVisible();
  await expect(next).toBeEnabled();
  // Subtitles can be turned off.
  await lesson.getByRole("checkbox", { name: "Tiếng Việt" }).uncheck();
  for (
    let i = 0;
    i < 20 &&
    !(await lesson.getByText("Xong bài học", { exact: false }).count());
    i++
  ) {
    if (await lesson.locator(".nt-options button:not([disabled])").count())
      await lesson.getByRole("button", { name: "since January" }).click();
    await next.click();
  }
  await expect(lesson.getByRole("link", { name: "Luyện tập" })).toHaveAttribute(
    "href",
    "/on-tap/phan/present-perfect-vs-past",
  );
});

test("a learner who is not a draft learner gets no sample lesson", async ({
  page,
}) => {
  await asLearner(page, null);
  await page.goto("/hoc/present-perfect-vs-past");
  await expect(
    page
      .getByText("Phần này chưa có bài học.", { exact: false })
      .or(page.getByRole("alert")),
  ).toBeVisible();
});
