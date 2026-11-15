// Sena, NodeTrail's mascot, rebuilt from the owner's model sheet (outputs/design/ui-v2/, specs/ui-v2).
// One body for every pose; only eyes, brows, mouth, hands and a prop change. Static markup, no user input.

export const SENA_POSES = [
  "idle",
  "wave",
  "focus",
  "heart",
  "oops",
  "think",
  "sleep",
] as const;
export type SenaPose = (typeof SENA_POSES)[number];

const esc = (s: string) =>
  s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");

const C = {
  fur: "#886244",
  furDark: "#6f4e35",
  skin: "#f4d6b2",
  earIn: "#e9bf98",
  hair: "#231d1a",
  hairLine: "#4a3b33",
  sweater: "#f1ece4",
  collar: "#e4d8c6",
  knit: "#c7a27e",
  indigo: "#4339ca",
  indigoHi: "#6267f5",
  cheek: "#f2a99a",
  mouth: "#8a2f2b",
  tongue: "#f08b86",
  eye: "#1d2140",
  silver: "#cfd8e3",
};

function eyes(pose: SenaPose): string {
  const L = 96,
    R = 144,
    Y = 140;
  const white = (x: number) =>
    `<circle cx="${x}" cy="${Y}" r="17" fill="#fff"/>`;
  const pupil = (x: number, dx = 2, dy = 2, r = 11) =>
    `<circle cx="${x + dx}" cy="${Y + dy}" r="${r}" fill="${C.eye}"/>` +
    `<circle cx="${x + dx + 4}" cy="${Y + dy - 4}" r="3.6" fill="#fff"/>` +
    `<circle cx="${x + dx - 4}" cy="${Y + dy + 4}" r="1.6" fill="#fff" opacity=".8"/>`;
  const closed = (x: number) =>
    `<path d="M${x - 13} ${Y + 1}q13 10 26 0" stroke="${C.hair}" stroke-width="4" stroke-linecap="round" fill="none"/>`;
  switch (pose) {
    case "sleep":
      return closed(L) + closed(R);
    case "heart":
      // content, lids a little lower
      return (
        `<g class="sena-eyes">${white(L)}${white(R)}${pupil(L, 1, 3)}${pupil(R, 1, 3)}` +
        `<path d="M${L - 18} ${Y - 9}h36M${R - 18} ${Y - 9}h36" stroke="${C.skin}" stroke-width="9"/>` +
        `<path d="M${L - 16} ${Y - 5}q16-6 32 0M${R - 16} ${Y - 5}q16-6 32 0" stroke="${C.hair}" stroke-width="3.2" stroke-linecap="round" fill="none"/></g>`
      );
    case "focus":
      return (
        `<g class="sena-eyes">${white(L)}${white(R)}${pupil(L, 0, 3)}${pupil(R, 0, 3)}` +
        `<path d="M${L - 18} ${Y - 10}h36M${R - 18} ${Y - 10}h36" stroke="${C.skin}" stroke-width="10"/>` +
        `<path d="M${L - 16} ${Y - 6}h32M${R - 16} ${Y - 6}h32" stroke="${C.hair}" stroke-width="3.4" stroke-linecap="round"/></g>`
      );
    case "oops":
      return (
        `<g class="sena-eyes">${white(L)}${white(R)}` +
        `<circle cx="${L}" cy="${Y}" r="6" fill="${C.eye}"/><circle cx="${R}" cy="${Y}" r="6" fill="${C.eye}"/></g>`
      );
    case "think":
      return `<g class="sena-eyes">${white(L)}${white(R)}${pupil(L, 5, -3)}${pupil(R, 5, -3)}</g>`;
    default:
      return `<g class="sena-eyes">${white(L)}${white(R)}${pupil(L)}${pupil(R)}</g>`;
  }
}

function brows(pose: SenaPose): string {
  const b = (d: string) =>
    `<path d="${d}" stroke="${C.hair}" stroke-width="5" stroke-linecap="round" fill="none"/>`;
  switch (pose) {
    case "focus":
      return b("M80 114q14-6 28 2") + b("M132 116q14-8 28-2");
    case "oops":
      return b("M82 112q12-10 26-3") + b("M132 109q14-7 26 3");
    case "think":
      return b("M82 116q13-4 26 0") + b("M132 108q14-8 28 0");
    case "sleep":
      return b("M84 120q12-4 24 0") + b("M132 120q12-4 24 0");
    default:
      return b("M80 116q15-10 30-2") + b("M130 114q15-8 30 2");
  }
}

function mouth(pose: SenaPose): string {
  switch (pose) {
    case "wave":
    case "idle":
      return (
        `<path d="M104 180h32q-2 18-16 18t-16-18z" fill="${C.mouth}"/>` +
        `<path d="M110 192q10-7 20 0q-4 6-10 6t-10-6z" fill="${C.tongue}"/>`
      );
    case "heart":
      return `<ellipse cx="120" cy="186" rx="7" ry="4.5" fill="#d9605a"/>`;
    case "focus":
      return ""; // hidden behind the finger
    case "oops":
      return ""; // hand over mouth
    case "think":
      return `<path d="M110 188q5-4 10 0t10 0" stroke="${C.mouth}" stroke-width="3.4" stroke-linecap="round" fill="none"/>`;
    case "sleep":
      return `<ellipse cx="120" cy="187" rx="5" ry="6" fill="${C.mouth}"/>`;
    default:
      return "";
  }
}

function hand(x: number, y: number, r = 13): string {
  return `<circle cx="${x}" cy="${y}" r="${r}" fill="${C.fur}"/>`;
}

function arms(pose: SenaPose): { back: string; front: string } {
  // back: the sleeve (drawn behind the head); front: the hand when it is at the face
  const sleeve = (d: string) =>
    `<path d="${d}" fill="${C.sweater}" stroke="${C.collar}" stroke-width="1.5"/>`;
  switch (pose) {
    case "wave":
      return {
        back: "",
        front: `<g class="sena-wave">${sleeve("M70 238q-26-28-30-64l20-6q8 30 28 50z")}${hand(48, 168, 14)}</g>`,
      };
    case "focus":
      return {
        back: sleeve("M70 240q20-28 38-36l10 10q-16 12-32 36z"),
        front:
          `<rect x="115" y="172" width="10" height="28" rx="5" fill="${C.furDark}"/>` +
          hand(120, 206, 13),
      };
    case "heart":
      return {
        back: sleeve("M66 240q-12-30 0-50l18 4q-8 22 0 46z"),
        front:
          `<path d="M70 194l8-24 8 3-6 23z" fill="${C.furDark}"/>` +
          hand(78, 198, 12) +
          `<path class="sena-prop" d="M64 160c-6-8 4-16 10-8c6-8 16 0 10 8l-10 10z" fill="#ef6f86"/>`,
      };
    case "oops":
      return {
        back: sleeve("M70 240q20-30 36-40l14 10q-16 12-30 36z"),
        front:
          `<g fill="${C.furDark}"><rect x="103" y="168" width="9" height="22" rx="4.5"/><rect x="112" y="164" width="9" height="26" rx="4.5"/><rect x="121" y="164" width="9" height="26" rx="4.5"/><rect x="130" y="168" width="9" height="22" rx="4.5"/></g>` +
          `<ellipse cx="120" cy="192" rx="21" ry="15" fill="${C.furDark}"/>`,
      };
    case "think":
      return {
        back: sleeve("M70 240q12-28 28-40l14 8q-12 14-22 40z"),
        front: hand(104, 204, 12),
      };
    default:
      return {
        back: sleeve("M66 240q-8-20-4-40l18 2q-2 18 4 38z") + hand(66, 262, 12),
        front: "",
      };
  }
}

function prop(pose: SenaPose): string {
  if (pose === "think")
    return (
      `<g class="sena-prop"><circle cx="196" cy="40" r="20" fill="${C.indigo}"/>` +
      `<text x="196" y="48" text-anchor="middle" font-family="system-ui,sans-serif" font-weight="800" font-size="24" fill="#fff">?</text>` +
      `<circle cx="176" cy="66" r="4" fill="${C.indigo}"/></g>`
    );
  if (pose === "sleep")
    return (
      `<g class="sena-prop" fill="${C.indigo}" font-family="system-ui,sans-serif" font-weight="800">` +
      `<text x="178" y="52" font-size="20">z</text><text x="196" y="34" font-size="13">z</text></g>`
    );
  if (pose === "oops")
    return `<path class="sena-prop" d="M178 92q6 10 0 14q-6-4 0-14z" fill="#79c4ea"/>`;
  return "";
}

function knit(id: string): string {
  // the "NT" monogram knit, clipped to the sweater
  let s = "";
  const rows: [number, [number, string][]][] = [
    [
      214,
      [
        [84, "d"],
        [110, "NT"],
        [150, "d"],
      ],
    ],
    [
      238,
      [
        [70, "d"],
        [98, "NT"],
        [136, "d"],
        [156, "NT"],
      ],
    ],
    [
      262,
      [
        [84, "NT"],
        [126, "d"],
        [140, "NT"],
      ],
    ],
    [
      286,
      [
        [70, "d"],
        [98, "NT"],
        [136, "d"],
        [156, "NT"],
      ],
    ],
  ];
  rows.forEach(([y, cells]) =>
    cells.forEach(([x, k]) => {
      s +=
        k === "d"
          ? `<rect x="${x - 4}" y="${y - 9}" width="8" height="8" transform="rotate(45 ${x} ${y - 5})" fill="${C.knit}"/>`
          : `<text x="${x}" y="${y}" font-family="Georgia,'Times New Roman',serif" font-weight="700" font-size="13" fill="${C.knit}">NT</text>`;
    }),
  );
  return `<g clip-path="url(#${id}-body)">${s}</g>`;
}

/** The SVG markup for one pose; `id` must be unique on the page (clip path). */
export function senaSvg(pose: SenaPose, id: string, label: string): string {
  const arm = arms(pose);
  return `<svg class="sena sena--${pose}" viewBox="0 0 240 300" role="img" aria-label="${esc(label)}" xmlns="http://www.w3.org/2000/svg">
<defs><clipPath id="${id}-body"><path d="M66 214q54-22 108 0l14 86H52z"/></clipPath></defs>
<g class="sena-tail"><path d="M168 268c40 0 56-28 50-56-5-24-34-26-36-8-1 10 10 14 16 8" stroke="${C.fur}" stroke-width="12" stroke-linecap="round" fill="none"/></g>
<g class="sena-body">
<path d="M66 214q54-22 108 0l14 86H52z" fill="${C.sweater}"/>
${knit(id)}
<ellipse cx="120" cy="212" rx="40" ry="11" fill="${C.collar}"/>
${arm.back}
<g transform="rotate(-14 170 256)"><rect x="150" y="234" width="40" height="44" rx="5" fill="${C.indigo}"/><rect x="155" y="239" width="30" height="34" rx="3" fill="${C.indigoHi}"/><path d="M170 244v12" stroke="#c8ccff" stroke-width="2.4" stroke-linecap="round"/></g>
${hand(176, 274, 13)}
</g>
<g class="sena-head">
<circle cx="40" cy="124" r="30" fill="${C.fur}"/><circle cx="40" cy="124" r="18" fill="${C.earIn}"/>
<circle cx="200" cy="124" r="30" fill="${C.fur}"/><circle cx="200" cy="124" r="18" fill="${C.earIn}"/>
<circle cx="120" cy="132" r="80" fill="${C.fur}"/>
<path d="M120 112c-12-14-58-16-64 18-5 28 4 52 22 66 12 10 26 14 42 14s30-4 42-14c18-14 27-38 22-66-6-34-52-32-64-18z" fill="${C.skin}"/>
<path d="M44 112c-4-50 32-78 76-78s80 28 76 78l-10-12-8 6-10-12-12 10-10-12-12 10-14-10-14 10-12-10-10 12-12-10-10 12-8-6z" fill="${C.hair}"/>
<path d="M76 54l5 26M97 44l3 30M120 41v32M143 44l-3 30M164 54l-5 26" stroke="${C.hairLine}" stroke-width="2.4" stroke-linecap="round"/>
${brows(pose)}
${eyes(pose)}
<ellipse cx="78" cy="170" rx="13" ry="8" fill="${C.cheek}" opacity=".75"/>
<ellipse cx="162" cy="170" rx="13" ry="8" fill="${C.cheek}" opacity=".75"/>
<ellipse cx="113" cy="166" rx="3.4" ry="2.6" fill="#6b4630"/><ellipse cx="127" cy="166" rx="3.4" ry="2.6" fill="#6b4630"/>
${mouth(pose)}
<path d="M56 147q-2 52 58 76M184 147q2 52-58 76" stroke="#fff" stroke-width="2.2" fill="none"/>
<circle cx="58" cy="138" r="9" fill="#fff" stroke="${C.silver}" stroke-width="2.4"/><circle cx="58" cy="138" r="3.4" fill="${C.silver}"/>
<circle cx="182" cy="138" r="9" fill="#fff" stroke="${C.silver}" stroke-width="2.4"/><circle cx="182" cy="138" r="3.4" fill="${C.silver}"/>
<circle cx="208" cy="148" r="5" fill="${C.silver}" stroke="#a8b3c2" stroke-width="1.4"/>
${arm.front}
</g>
${prop(pose)}
</svg>`;
}
