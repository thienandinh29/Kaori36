"use client";
import { useEffect, useId, useRef } from "react";
import { senaSvg, type SenaPose } from "@/lib/sena";

/** Sena in one pose. Changing `pose` swaps the drawing with a small pop (none under reduced motion). */
export function Sena({
  pose,
  label,
  className,
}: {
  pose: SenaPose;
  label: string;
  className?: string;
}) {
  const id = "sena" + useId().replace(/[^a-zA-Z0-9]/g, "");
  const ref = useRef<HTMLSpanElement>(null);
  const first = useRef(true);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (first.current) {
      first.current = false;
      return;
    }
    el.classList.remove("sena-pop");
    void el.offsetWidth; // restart the animation
    el.classList.add("sena-pop");
  }, [pose]);
  return (
    <span
      ref={ref}
      className={`sena-box${className ? " " + className : ""}`}
      // static markup built from typed constants (lib/sena.ts); the label is escaped there
      dangerouslySetInnerHTML={{ __html: senaSvg(pose, id, label) }}
    />
  );
}
