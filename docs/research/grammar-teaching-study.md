# How to teach grammar: what the research and good curricula say, and what NodeTrail takes

Written 2026-11-17 for `specs/grammar-lessons/` at the owner's request: study good English-teaching curricula, take the
best way to teach and the best path through grammar, adapt both, and use open sources for RAG.

**How this was read.** Web searches only: abstracts, publisher and library pages, and search-result excerpts. **No full
paper was read**, so effect sizes are quoted as reported elsewhere and flagged. Where the evidence is weak or mixed,
this note says so. Copyrighted curricula (English Grammar Profile, British Council/EAQUALS Core Inventory, Cambridge
course books) are used as **references for ideas and level order only**. Nothing from them is copied into the
product or the RAG library.

## 1. Teach rules explicitly, with examples first

- **Explicit instruction beats implicit.** Norris & Ortega (2000), a meta-analysis of 49 samples, found focused L2
  instruction gives large gains and explicit types beat implicit ones. Spada & Tomita (2010) found the same for both
  simple and complex English features. Effect sizes are left out because none was read in the papers themselves.
  ([Norris & Ortega record](https://www.deepdyve.com/lp/wiley/does-type-of-instruction-make-a-difference-substantive-findings-from-a-9dzVAhpcHv/),
  [Spada & Tomita record](https://www.bohrium.com/paper-details/interactions-between-type-of-instruction-and-type-of-language-feature-a-meta-analysis/811806560392052736-6763))
- **Caveat.** Critics note that these studies often measured with tests that favour explicit knowledge, and that only
  49 of about 250 candidate studies were included. Explicit teaching wins on the tests we also use (MCQ, gap-fill),
  which is the honest claim.
- **Taken.** Every lesson states the rule plainly, after the learner has **noticed** it in 2–3 contrasting examples
  ("guided discovery"). Making the learner look first, then telling the rule, combines discovery with explicit teaching.

## 2. The lesson shape: test → teach → test, with a "why" first

- **The usual frameworks.** Teacher-training material such as the Cambridge TKT syllabus describes three:
  - **PPP** (present, practise, produce);
  - **TTT** (test, teach, test);
  - **ESA** (engage, study, activate);

  plus task-based learning and guided discovery.
  ([TKT frameworks](https://open-exam-prep.com/study-guides/tkt-module1/background-to-language-teaching/teaching-frameworks))
- **Head-to-head evidence is thin:**
  - One small Iranian study found TTT beat a PPP-style group.
  - Another found PPP better for grammar recognition and tasks better for writing.

  No meta-analysis settles which is best.
  ([TTT study](https://journals.ikiu.ac.ir/article_1898_57dd9e7fdb992398d090b8106e85c084.pdf),
  [comparison](https://core.ac.uk/download/11493024.pdf))
- **Taken: TTT, because NodeTrail already works this way.**
  - The level test and the milestone test are the first "test".
  - "Tôi đã biết, kiểm tra luôn" (the owner keeps it) is TTT's skip for a learner who already knows the grammar.
  - The lesson is the "teach"; the node's practice and the milestone test are the second "test".
  - Inside the lesson we use ESA's order: **engage** (why you need it, an IELTS situation), **study** (meaning before
    form: concept questions and timelines, then the form table), **activate** (aided checkpoints).
  - Free production comes later, in Writing (phase 2), where the error map already feeds grammar nodes.

## 3. Meaning before form: concept-checking questions and timelines

- **What it is.** Standard teacher training checks meaning with **concept-checking questions** ("Is he still living in
  Hanoi? → yes") and draws **timelines** for tenses before showing the form. This is a practitioner consensus, not a
  measured effect.
- **Taken.** Each lesson has 2–3 yes/no concept questions after the examples (aided checkpoints). The board's
  `board_timeline` action draws past–now–future for every tense node.

## 4. Vietnamese learners: what to warn about

- **What the research finds.** Studies of Vietnamese learners agree on where errors come from. Vietnamese verbs do not
  change for tense or person, nouns do not change for plural, and there are no articles.
  - A Tra Vinh University study of 40 students found errors in subject–verb agreement in 100% of learners, noun plural
    -s in 97.5% and tense/aspect in 85%.
  - Other Vietnamese studies list tense, verb form, agreement, sentence structure, articles and plurals.
  ([CTU study](https://ctujs.ctu.edu.vn/index.php/ctujs/article/download/15/15),
  [TNU study](https://vjol.vista.gov.vn/tnu/en/article/view/104134),
  [SJSU guide](https://gcp-web.sjsu.edu/wac/docs/VietnameseEnglishGuide.pdf))
- **Caveat.** These are small samples, and only the abstracts were read.
- **Taken:**
  - Every lesson has a **"So với tiếng Việt"** (compared with Vietnamese) scene linked to the misconceptions the
    questions already test.
  - Endings (third-person -s, plural -s, past -ed) and articles come back **in later lessons as a spiral**: each later
    node's lesson has a short reminder when it uses them, not one lesson and done.

## 5. The order of grammar

- **What predicts order.**
  - **Natural order.** Learners acquire English morphemes in a broadly stable order (Dulay & Burt; Goldschneider &
    DeKeyser 2001, 12 studies, 924 learners). Five factors explain much of that order: perceptual salience, semantic
    complexity, regularity, syntactic category and frequency. Third-person -s comes **late** even though it is taught
    early, because it carries little meaning, is hard to hear and is irregular in use. So teaching it once early is not
    enough; it needs the spiral above.
    ([meta-analysis record](https://eric.ed.gov/?id=EJ718472))
  - **The level curricula.** The British Council/EAQUALS Core Inventory and the English Grammar Profile list which
    grammar appears at which CEFR level.
    - The Core Inventory's notice is "Copyright British Council/EAQUALS" and no open licence was found, so it is a
      reference for **level order only**.
      ([Core Inventory](https://www.eaquals.org/resources/the-core-inventory-for-general-english/),
      [validation](https://www.britishcouncil.org/research-insight/validating-core-inventory-general-english))
    - The English Grammar Profile is already excluded in `data/sources/english-candidates.yaml` (restricted use).
- **Taken: the proposed path** below orders milestones by CEFR level, then by what each needs first, then by
  learnability. It puts Vietnamese L1 trouble spots early **and** revisits them, and adds what IELTS Writing and
  Speaking need (linking, relative clauses, modals, passive variety, hedging).

## 6. Practice spaced over time

- **What the research finds.**
  - Spaced practice beats massed practice for L2 grammar and vocabulary in most studies (Miles 2014 for receptive
    grammar; Suzuki & DeKeyser 2017).
  - The best gap is unsettled, and one 2024 retrieval study found no advantage for spacing.
  - Practice should be hard enough to need effort but not so hard it fails ("desirable difficulty", Suzuki, Nakata &
    DeKeyser 2019).
  ([spacing review](https://www.cambridge.org/core/services/aop-cambridge-core/content/view/S0272263121000358),
  [Rogers](https://ira.lib.polyu.edu.hk/bitstream/10397/113055/1/Rogers_Optimizing_Distributed_Practice.pdf))
- **Taken.**
  - FSRS already schedules vocabulary; grammar nodes that reach mastery get spaced review items the same way.
  - Reviews mix earlier grammar in (interleaving) rather than repeating the node just studied.
  - Gaps follow FSRS, not a fixed number.

## 7. Hearing English with two subtitles

- **What the research finds.**
  - Meta-analyses find captions help L2 listening and vocabulary (Montero-Pérez et al.; Alotaibi et al. 2023).
  - Studies suggest the two kinds help differently. **L1 subtitles** (Vietnamese) mainly help understanding the
    content. **L2 captions** (English) help vocabulary and grammar noticing.
  - Mayer's "redundancy principle" warns against narration plus identical text, but **Lee & Mayer (2018)** found L2
    learners did *better* with narration plus on-screen text, a boundary condition for second-language learners.
  - Another study found captions did not help learners without spare capacity.
  ([captions meta-analysis](https://mdpi.com/2079-8954/10/5/133),
  [subtitles meta-analysis](https://ouci.dntb.gov.ua/works/4MXGMPx7),
  [L1 vs L2](https://mdpi.com/2227-7102/13/3/274),
  [Lee & Mayer 2018](https://zendy.io/title/10.1002/acp.3436))
- **Taken (the owner's decision 3).**
  - Sena **speaks English**.
  - The English caption highlights the target form, and the Vietnamese subtitle sits under it.
  - Each can be turned off, and both are on by default.
  - Overload is controlled by keeping the narration short and **graded** (section 8).

## 8. Improvements on OpenMAIC

OpenMAIC generates lessons with a model and lets agents run the class. This design keeps its scene and action
language (see `openmaic-study.md`, idea 1) and adds what fits a mastery-tracking tutor:

1. **The narration is graded English, checked by code.** Every narration word must be in our word list (NGSL/NAWL
   plus the authored list) at or below the lesson's level, plus the grammar terms the lesson teaches. A sentence that
   fails is rewritten before review. The 3,663-word list we just imported makes this checkable.
2. **The engine chooses scenes.** After a wrong answer on misconception M, the engine can replay the scene tagged
   with M, and the "Vì sao?" trace shows it. OpenMAIC has no per-concept learner model; we have BKT.
3. **Evidence is weighted.**
   - Reading a lesson is no evidence.
   - Checkpoints are aided evidence.
   - Practice and tests are unaided evidence.
   - Mastery needs unaided correct answers (`specs/mastery-gate/`).
4. **Every rule is cited.**
   - Each "study" scene cites RAG chunks of a licence-verified source.
   - A second model family answers the scene's concept questions blind from those chunks only.
   - The page shows "Nguồn".
5. **Generated once, played the same way every time.** Lessons are generated offline and reviewed, so each learner
   sees the same checked lesson and playback has no model cost.
6. **Measured.** The report gives first-try accuracy with versus without the lesson, the scene where learners stop,
   and the owner's ratings.

## 9. Open sources found

**Update 17 Nov 2026.** Each licence was read on the source's own page and each level skimmed; the results are in
`data/sources/english-candidates.yaml`:
- Bissonnette: CC BY-NC 4.0, A1–C1, the backbone.
- Al Haider High-Intermediate: CC BY 4.0, B1–B2.
- Explorations 1: CC BY-NC-SA 4.0, four A1 chapters only.
- Wikibooks: CC BY-SA 4.0, but a school grammar for native speakers, so it does not fill the A1–B1 gap.
- Haisley: CC BY 4.0, but a linguistics textbook. Rejected as a lesson source and kept as a backup for terms.
- Ferguson's grammar slides: no licence declared, so rejected.

No CC BY grammar text for A1–B1 was found. The table below is the first list, from before the check.

| Source | Licence reported | Level, use | Note |
|---|---|---|---|
| *Advanced Academic Grammar for ESL Students*, R. Al Haider (Reedley College) | CC BY (Open Textbook Library, BCcampus) | B2–C1 academic grammar, close to IELTS Writing | best fit for the B2–C1 nodes |
| *A Concise Guide to English Grammar*, P. Haisley (2026) | CC BY 4.0 (its colophon) | general grammar reference | very new; level unknown; read before relying on it |
| *Explorations 1: Grammar for the Experienced Beginner*, Open Oregon (2021) | CC BY-NC-SA 4.0 | A1–A2 | NonCommercial: flagged, allowed for study |
| *ESL Grammar The Way You Like It*, Bissonnette (LibreTexts) | CC BY-NC 4.0 | ESL grammar | NonCommercial: flagged |
| Wikibooks, *English Grammar* | believed CC BY-SA 4.0 | reference | already a candidate |

([OTL listing](https://open.umn.edu/opentextbooks/textbooks/1074),
[Haisley colophon](https://phil-a-sophist.github.io/concise-guide-english-grammar/front-colophon.html),
[Explorations 1](https://openoregon.pressbooks.pub/explorations1/),
[Bissonnette](https://human.libretexts.org/Bookshelves/Languages/English_as_a_Second_Language/ESL_Grammar_The_Way_You_Like_It_(Bissonnette)))

**Licence placement.** CC BY material can go anywhere with attribution. CC BY-SA goes in `data-sa/`. NC material
stays in `data/` (CC BY-NC-SA), which is already NonCommercial. No source with NoDerivatives is used.

**Network.** This cloud session could not open open.umn.edu or en.wikibooks.org, so those hosts must be allowed
before the RAG fetch. The owner's laptop is not limited.
