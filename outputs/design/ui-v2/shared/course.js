/*
 * Shared content for the three directions. The graph is the real English
 * course (data/courses/english-ielts.yaml): 10 milestones, 19 hidden nodes,
 * CEFR levels and prerequisite edges copied from it. The p_known values are
 * ILLUSTRATIVE (a made-up learner around B1) and every page says so.
 */
(function () {
  const milestones = [
    { slug: "present-tenses", short: "Thì hiện tại", name: "Các thì hiện tại", level: "A2", needs: [], hidden: [
      ["be-present", "Động từ to be (am, is, are)", "A1", 0.97],
      ["present-simple", "Thì hiện tại đơn", "A1", 0.92],
      ["present-continuous", "Thì hiện tại tiếp diễn", "A2", 0.88] ] },
    { slug: "nouns-articles", short: "Danh từ, mạo từ", name: "Danh từ và mạo từ", level: "A2", needs: [], hidden: [
      ["plural-nouns", "Danh từ số nhiều", "A1", 0.95],
      ["articles-basic", "Mạo từ a, an, the", "A1", 0.58],
      ["there-is-are", "There is / there are", "A1", 0.86] ] },
    { slug: "past-and-future", short: "Quá khứ, tương lai", name: "Quá khứ đơn và tương lai", level: "A2", needs: ["present-tenses"], hidden: [
      ["past-simple", "Thì quá khứ đơn", "A2", 0.79],
      ["future-will-going-to", "Will và going to", "A2", 0.46] ] },
    { slug: "comparison", short: "So sánh", name: "So sánh", level: "A2", needs: ["present-tenses"], hidden: [
      ["comparatives", "So sánh hơn", "A2", 0.91],
      ["superlatives", "So sánh nhất", "A2", 0.87] ] },
    { slug: "perfect-tenses", short: "Hoàn thành", name: "Hiện tại hoàn thành", level: "B1", needs: ["past-and-future"], hidden: [
      ["present-perfect-form", "Cấu trúc, ever và never", "B1", 0.41],
      ["present-perfect-vs-past", "Hoàn thành hay quá khứ đơn", "B1", 0.18] ] },
    { slug: "conditionals-1-2", short: "Điều kiện 1–2", name: "Câu điều kiện loại 1 và 2", level: "B1", needs: ["past-and-future"], hidden: [
      ["first-conditional", "Điều kiện loại 1", "B1", 0.52],
      ["second-conditional", "Điều kiện loại 2", "B1", 0.21] ] },
    { slug: "passive", short: "Bị động", name: "Câu bị động", level: "B1", needs: ["past-and-future"], hidden: [
      ["passive-present-past", "Bị động hiện tại và quá khứ", "B1", 0.14] ] },
    { slug: "narrative-tenses", short: "Thì kể chuyện", name: "Các thì kể chuyện", level: "B2", needs: ["perfect-tenses"], hidden: [
      ["past-continuous", "Quá khứ tiếp diễn", "B1", 0.33],
      ["past-perfect", "Quá khứ hoàn thành", "B2", 0.06] ] },
    { slug: "conditional-3", short: "Điều kiện 3", name: "Câu điều kiện loại 3", level: "B2", needs: ["conditionals-1-2", "narrative-tenses"], hidden: [
      ["third-conditional", "Điều kiện loại 3", "B2", 0.04] ] },
    { slug: "conditionals-mixed", short: "Điều kiện hỗn hợp", name: "Câu điều kiện hỗn hợp", level: "C1", needs: ["conditional-3"], hidden: [
      ["mixed-conditionals", "Điều kiện hỗn hợp", "C1", 0.02] ] },
  ].map((m) => ({
    ...m,
    hidden: m.hidden.map(([slug, name, level, p]) => ({ slug, name, level, p })),
  }));

  const band = (p) => (p >= 0.85 ? "strong" : p >= 0.5 ? "growing" : "gap");
  const bandVi = { strong: "Vững", growing: "Đang lên", gap: "Còn hổng" };
  milestones.forEach((m) => {
    m.p = m.hidden.reduce((s, h) => s + h.p, 0) / m.hidden.length;
    m.counts = { strong: 0, growing: 0, gap: 0 };
    m.hidden.forEach((h) => m.counts[band(h.p)]++);
    m.band = band(m.p);
  });
  const all = milestones.flatMap((m) => m.hidden);
  const totals = { strong: 0, growing: 0, gap: 0 };
  all.forEach((h) => totals[band(h.p)]++);

  const pct = (p) => Math.round(p * 100) + "%";
  const dec = (p) => p.toFixed(2).replace(".", ","); // Vietnamese decimal comma

  window.Course = {
    title: "Ngữ pháp tiếng Anh cho IELTS",
    levels: ["A1", "A2", "B1", "B2", "C1"],
    milestones,
    bySlug: Object.fromEntries(milestones.map((m) => [m.slug, m])),
    all,
    totals,
    band,
    bandVi,
    pct,
    dec,
    learnNext: { milestone: "perfect-tenses", node: "present-perfect-form" },
    estimate: "B1 (ước lượng)",
    dueReviews: 6,
    illustrative: "Số liệu minh hoạ, chưa phải dữ liệu học của bạn",
    trace:
      "Bạn đã vững “Quá khứ đơn” (0,79 → đủ làm nền). Trong các phần mở tiếp theo, “Cấu trúc hiện tại hoàn thành” có mức nắm vững thấp nhất (0,41) mà mọi phần nền đã đủ, nên Sena chọn phần này trước “Hoàn thành hay quá khứ đơn” (0,18, cần phần trước).",
    quiz: {
      prompt: "I ___ in Hà Nội since 2020.",
      options: ["lived", "have lived", "live", "am living"],
      key: "have lived",
      wrong: {
        lived: "Có “since” nên hành động kéo dài tới bây giờ: dùng hiện tại hoàn thành, không dùng quá khứ đơn.",
        live: "Hiện tại đơn không nối được quá khứ với hiện tại. “since 2020” cần have/has + V3.",
        "am living": "Tiếp diễn nhấn mạnh lúc này; với “since” để nói một quãng tới nay, dùng hiện tại hoàn thành.",
      },
      right: "Đúng rồi. “since 2020” nối quá khứ với hiện tại nên dùng have lived.",
    },
  };
})();
