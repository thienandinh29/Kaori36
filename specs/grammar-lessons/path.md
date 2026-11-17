# The grammar path (proposed)

The machine-checked version is `english-ielts-path.yaml` next to this file. `python -m app.curriculum.check` passes:
28 milestones and 51 hidden nodes, no cycles, no prerequisite above the level of what needs it. **It is not live.** The
app still serves `data/courses/english-ielts.yaml` (10 milestones, 19 nodes). A node goes live when it has questions
and a lesson. The 29 existing nodes keep their slugs, so no learner progress moves.

## How it is ordered
1. **By CEFR level.** The British Council/EAQUALS Core Inventory and our own judgement are used for the level of each
   point. The inventory is used for order only (copyrighted, nothing copied).
2. **Then by what each point needs first.** Prerequisites are drawn only where one point is built on another (for
   example, past perfect before reported statements, or `wh-` questions before reported questions).
3. **Then by learnability.** Salient, frequent, regular forms come before late-acquired ones (Goldschneider &
   DeKeyser).
4. **IELTS needs are added from B1.** These are linking words for coherence, relative clauses and noun phrases for
   Writing Task 2, modals of deduction and hedging for academic tone, and passive variety for Task 1 processes.

## The spiral (Vietnamese learners)
Endings and articles are taught early **and come back**. In each node below, the lesson has a short reminder ("Nhớ
lại") and the practice includes at least one question on the earlier point.

| Point | Taught in | Comes back in |
|---|---|---|
| third-person -s | `present-simple` | `present-perfect-form` (has), `passive-present-past` (is/was), `agreement-long-subjects` |
| plural -s | `plural-nouns` | `countable-uncountable`, `quantifiers-basic`, `agreement-long-subjects` |
| past -ed and V3 | `past-simple` | `present-perfect-form`, `passive-present-past`, `past-perfect`, `participle-clauses-node` |
| articles | `articles-basic` | `countable-uncountable`, `superlatives` (the), `defining-relative`, `generic-zero-article`, `nominalisation` |
| tense choice | `present-continuous`, `past-simple` | `present-perfect-vs-past`, `past-continuous`, `reported-statements` |

## The path, with where each lesson's content comes from
Sources (licences read 17 Nov 2026, `data/sources/english-candidates.yaml`):
- **B**: Bissonnette, *ESL Grammar The Way You Like It*, CC BY-NC 4.0. Cited as book.chapter.
- **AH**: Al Haider, *High-Intermediate Academic Grammar*, CC BY 4.0.
- **E1**: *Explorations 1*, CC BY-NC-SA 4.0.
- **HW**: Hall and Wallace, *College ESL Writers*, CC BY-NC-SA. Added 17 Nov, after the gap search.

Matched **by chapter title only**; the chapters themselves have not been read yet. **—** means no chapter was found,
so there is no cited lesson yet.

| Level | Milestone (+ = new) | Nodes | Source chapters | IELTS use |
|---|---|---|---|---|
| A2 | present-tenses | be-present · present-simple · present-continuous | E1 1–4; B 1.02, 1.06, 1.07, 2.10, 2.13 | describing habits and now |
| A2 | nouns-articles | plural-nouns · articles-basic · there-is-are · **+countable-uncountable · +quantifiers-basic** | B 2.09 (noun spelling); HW 7.04 (articles, count and noncount); there is: **—** | accurate noun phrases in every task |
| A1 | **+pronouns-possessives** | subject-object-pronouns · possessives | HW 7.05, 7.06; B 1.05 | |
| A2 | **+questions-negatives** | yes-no-questions · wh-questions | B 2.11, 2.12, 2.14; HW 7.03 (negatives) | Speaking: asking and answering |
| A2 | past-and-future | past-simple · future-will-going-to | B 1.09, 2.04; AH (simple future) | Speaking Part 2 stories |
| A2 | **+modals-basic** | can-ability · must-have-to | B 2.05 | rules and obligations |
| A2 | comparison | comparatives · superlatives | B 2.06, 3.09 | Task 1 comparisons |
| A2 | **+prepositions-time-place** | prepositions-time · prepositions-place | B 2.08, 4.01; HW 7.11 | Task 1 dates and places |
| B1 | perfect-tenses | present-perfect-form · present-perfect-vs-past | B 3.04, 3.07; AH (present perfect) | Speaking Part 1 "How long…" |
| B1 | conditionals-1-2 | **+zero-conditional** · first-conditional · second-conditional | B 4.08, 5.03 | Task 2 proposals |
| B1 | passive | passive-present-past | B 4.03; AH (passive) | Task 1 processes |
| B1 | **+verb-patterns** | gerund-infinitive · used-to | B 3.08; AH (gerunds and infinitives); used to: **—** | |
| B1 | **+relative-clauses** | defining-relative | B 4.07; AH (adjective clauses) | Task 2 precise definitions |
| B1 | **+modals-advice-possibility** | should-advice · might-may | B 2.05; AH (modals) | Task 2 recommendations |
| B1 | **+linking-ideas** | linking-contrast · linking-cause-result | B 3.13, 3.14, 4.05, 4.06, 4.09, 4.13, 5.13; HW 2.02 | coherence and cohesion band |
| B2 | narrative-tenses | past-continuous · past-perfect | B 1.10, 3.06, 3.07 | Speaking Part 2 |
| B2 | conditional-3 | third-conditional | B 5.03 (partly) | |
| B2 | **+passive-advanced** | passive-all-tenses · impersonal-passive | B 4.02, 4.04 (partly); impersonal: **—** | Task 2 "It is often argued that" |
| B2 | **+reported-speech** | reported-statements · reported-questions | B 5.06; AH (reported speech, embedded questions) | reporting views in Task 2 |
| B2 | **+relative-clauses-advanced** | non-defining-relative | B 4.07; AH (adjective clauses) | |
| B2 | **+modals-deduction** | deduction-present · deduction-past | AH (modals, partly) | Speaking Part 3 speculation |
| B2 | **+articles-advanced** | generic-zero-article | HW 7.04 (partly: general use of the and no article) | Task 2 generalisations |
| B2 | **+agreement** | agreement-long-subjects | HW 7.10 | grammatical range and accuracy band |
| B2 | **+noun-phrases** | nominalisation | **—** (B 5.05 is noun clauses, a different point) | academic style |
| C1 | conditionals-mixed | mixed-conditionals | B 5.03 (partly) | |
| C1 | **+participle-clauses** | participle-clauses-node | **—** | concise Task 2 sentences |
| C1 | **+emphasis** | negative-inversion · cleft-sentences | B 5.12 (negative adverbs); cleft: **—** | range at band 7+ |
| C1 | **+hedging** | hedging-language | **—** | Task 2 academic caution |

## The gaps, and what to do about them
**Update 17 Nov (the gap search).** *College ESL Writers* (HW, CC BY-NC-SA) fills these:
- articles;
- count and noncount nouns;
- pronouns;
- negatives;
- subject–verb agreement.

*A Digital Workbook for Beginning ESOL* (**CC BY 4.0, read by the owner 17 Nov**) has an articles chapter: the one
CC BY source for beginners.

Still no verified source for:
- there is/are;
- used to;
- nominalisation;
- participle clauses;
- cleft sentences;
- hedging;
- the impersonal passive.

Options, for the owner:
1. **Look for one more source on these points** (done 17 Nov for articles, see above). For the remaining C1
   academic points (nominalisation, hedging, participle clauses), the open options found so far are not ESL texts.
2. **Authored lessons for the gaps.** We write them in our own words, labelled "Bản nháp — tự soạn, chưa có nguồn".
   They are never shown as "Nguồn: <textbook>", and they are reviewed by the owner. This breaks "cited from a
   source" for these nodes only and says so on the page.
3. **Leave those nodes without a lesson.** The map shows practice and the test only, as today.

## Not decided here
Which new milestones go live first is the owner's choice. The 18 new milestones bring 32 new nodes; at about 4 questions
each, that is about 130 new questions, plus a lesson per node. A sensible first batch is the A2–B1 additions with sources:
questions-negatives, modals-basic, prepositions-time-place, verb-patterns (without used to), relative-clauses,
modals-advice-possibility and linking-ideas.
