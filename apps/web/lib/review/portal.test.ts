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
});
