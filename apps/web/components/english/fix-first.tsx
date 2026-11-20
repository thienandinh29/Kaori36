"use client";
import { useEffect, useState } from "react";
import { englishClient } from "@/lib/english/client";
import {
  fixFirst,
  styleFor,
  type Priority,
  type Style,
} from "@/lib/english/priorities";
import type { EssayResult, GrammarIssue, Level } from "@/lib/english/types";
import { vi } from "@/messages/vi";
import { Marked } from "./marked";

const w = vi.english.writing;
const STYLE_KEY = "nodetrail_fix_style";

function storedStyle(): Style | null {
  try {
    const s = window.localStorage.getItem(STYLE_KEY);
    return s === "direct" || s === "indirect" ? s : null;
  } catch {
    return null;
  }
}

/** One repeated error: direct shows the fix; indirect names the error and lets the learner try. */
function Pattern({
  issue,
  count,
  style,
}: {
  issue: GrammarIssue;
  count: number;
  style: Style;
}) {
  const [shown, setShown] = useState(false);
  return (
    <>
      <span className="en-badge">
        {w.fixRepeated.replace("{n}", String(count))}
      </span>{" "}
      <strong>{issue.node_vi ?? w.fixOtherError}</strong>
      <Marked issue={issue} />
      {issue.explain_vi && <p>{issue.explain_vi}</p>}
      {issue.suggestion !== null &&
        (style === "direct" || shown ? (
          <p>
            {w.suggestion}: <strong lang="en">{issue.suggestion}</strong>
          </p>
        ) : (
          <button
            type="button"
            className="en-button small ghost"
            onClick={() => setShown(true)}
          >
            {w.fixShow}
          </button>
        ))}
    </>
  );
}

function Item({
  p,
  result,
  style,
}: {
  p: Priority;
  result: EssayResult;
  style: Style;
}) {
  switch (p.kind) {
    case "off_topic":
      return <p>{w.guardOffTopic}</p>;
    case "padded":
      return (
        <p>
          {w.guardPadded
            .replace("{r}", String(p.repeated))
            .replace("{t}", String(p.templated))}
        </p>
      );
    case "template":
      return (
        <>
          <p>{w.guardTemplate}</p>
          {p.phrases.map((x) => (
            <q key={x} lang="en">
              {x}
            </q>
          ))}
        </>
      );
    case "number":
      return <p>{w.fixNumber.replace("{n}", p.text)}</p>;
    case "overview":
      return <p>{w.fixOverview}</p>;
    case "feedback":
      return (
        <>
          <span className="en-badge">
            {p.criterion === "tr" && result.task === 1
              ? w.task1Criterion
              : w.criteria[p.criterion]}
          </span>{" "}
          {p.point.point_vi}
          {p.point.quotes.slice(0, 1).map((q) => (
            <q key={q} lang="en">
              {q}
            </q>
          ))}
        </>
      );
    case "pattern":
      return <Pattern issue={p.issues[0]!} count={p.count} style={style} />;
  }
}

/** "Sửa trước": at most five things to fix first (specs/writing/step-2.6.md). */
export function FixFirst({
  result,
  learner,
}: {
  result: EssayResult;
  learner?: string;
}) {
  const [level, setLevel] = useState<Level | null>(null);
  const [chosen, setChosen] = useState<Style | null>(storedStyle);
  useEffect(() => {
    if (!learner) return;
    let live = true;
    englishClient()
      .roadmap(learner)
      .then((r) => live && setLevel(r.level_test?.grammar_level ?? null))
      .catch(() => undefined); // no level: direct corrections
    return () => {
      live = false;
    };
  }, [learner]);
  const items = fixFirst(result);
  if (items.length === 0) return null;
  const style = chosen ?? styleFor(level);
  function choose(s: Style) {
    try {
      window.localStorage.setItem(STYLE_KEY, s);
    } catch {
      /* this page only */
    }
    setChosen(s);
  }
  return (
    <section className="en-card" data-testid="fix-first">
      <h2>{w.fixTitle}</h2>
      <p className="en-muted">{w.fixNote}</p>
      <div className="nt-actions" role="group" aria-label={w.fixStyle}>
        <button
          type="button"
          aria-pressed={style === "direct"}
          className={`en-button small ${style === "direct" ? "" : "ghost"}`}
          onClick={() => choose("direct")}
        >
          {w.fixDirect}
        </button>
        <button
          type="button"
          aria-pressed={style === "indirect"}
          className={`en-button small ${style === "indirect" ? "" : "ghost"}`}
          onClick={() => choose("indirect")}
        >
          {w.fixIndirect}
        </button>
      </div>
      <ol className="en-fix-first">
        {items.map((p, i) => (
          <li key={i} data-kind={p.kind}>
            <Item p={p} result={result} style={style} />
          </li>
        ))}
      </ol>
    </section>
  );
}
