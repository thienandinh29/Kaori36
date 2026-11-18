import { describe, expect, it, vi } from "vitest";
import { DataError } from "@/lib/decode";
import { parseMe, parseNext, pickToken, reviewClient } from "./portal";

const TOKEN = "a".repeat(43);

describe("reviewer portal helpers", () => {
  it("takes the token from the link and clears the address bar", () => {
    expect(pickToken(`#${TOKEN}`, null)).toEqual({ token: TOKEN, clear: true });
    expect(pickToken("", TOKEN)).toEqual({ token: TOKEN, clear: false });
    expect(pickToken("#bad", "also bad")).toEqual({ token: null, clear: true });
    expect(pickToken("", null)).toEqual({ token: null, clear: false });
  });

  it("decodes strictly", () => {
    expect(
      parseMe({
        name: "Cô Lan",
        role: "expert_teacher",
        batches: [
          {
            id: "b",
            name: "Đọc 1",
            content_type: "reading_item",
            total: 3,
            done: 1,
          },
        ],
      }).batches[0],
    ).toEqual({
      id: "b",
      name: "Đọc 1",
      contentType: "reading_item",
      total: 3,
      done: 1,
    });
    expect(() =>
      parseMe({ name: "x", role: "y", batches: [{ id: "b" }] }),
    ).toThrow(DataError);
    expect(
      parseNext({ total: 1, done: 1, unavailable: 0, item: null }).item,
    ).toBeNull();
    expect(
      parseNext({
        total: 1,
        done: 0,
        unavailable: 0,
        item: { content_type: "text_level", content_id: "bees", text: "Bees." },
      }).item,
    ).toEqual({ contentType: "text_level", contentId: "bees", text: "Bees." });
    expect(() =>
      parseNext({
        total: 1,
        done: 0,
        unavailable: 0,
        item: { content_type: "essay" },
      }),
    ).toThrow(DataError);
  });

  it("sends the token as a header, never in the URL", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ name: "n", role: "r", batches: [] })),
      );
    await reviewClient(TOKEN, fetcher).me();
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe("/api/backend/review/me");
    expect(String(url)).not.toContain(TOKEN);
    expect((init.headers as Record<string, string>)["X-Reviewer-Token"]).toBe(
      TOKEN,
    );
  });

  it("reports a revoked link as 401", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response("{}", { status: 401 }));
    await expect(reviewClient(TOKEN, fetcher).me()).rejects.toMatchObject({
      status: 401,
    });
  });

  it("decodes the V2b views", () => {
    const base = { total: 3, done: 0, unavailable: 0 };
    expect(
      parseNext({
        ...base,
        item: {
          content_type: "grammar_item",
          content_id: "g1",
          prompt: "My sister ___ a nurse.",
          options: ["are", "is"],
          key: 1,
        },
      }).item,
    ).toMatchObject({ contentType: "grammar_item", key: 1 });
    expect(
      parseNext({
        ...base,
        item: {
          content_type: "speech_target",
          content_id: "r:0",
          sentence: null,
          word: "think",
          ipa: "θ",
          sound_vi: null,
          start_ms: 100,
          end_ms: 180,
        },
      }).item,
    ).toMatchObject({ contentType: "speech_target", startMs: 100, endMs: 180 });
    expect(() =>
      parseNext({
        ...base,
        item: {
          content_type: "speech_target",
          content_id: "r:0",
          word: "x",
          start_ms: -1,
          end_ms: 1,
        },
      }),
    ).toThrow(DataError);
  });

  it("fetches a recording with the header, keeping ':' unencoded", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(new Blob(["RIFF"])));
    const id = "0b9d2f4e-1c2a-4d3b-8e5f-6a7b8c9d0e1f";
    const blob = await reviewClient(TOKEN, fetcher).audio("b", `${id}:2`);
    const [url, init] = fetcher.mock.calls[0];
    expect(url).toBe(`/api/backend/review/batches/b/items/${id}:2/audio`);
    expect((init.headers as Record<string, string>)["X-Reviewer-Token"]).toBe(
      TOKEN,
    );
    expect(await blob.text()).toBe("RIFF");
  });
});
