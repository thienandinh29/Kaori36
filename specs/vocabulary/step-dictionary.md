# Step: dictionary search over the word list (`/tu-dien`)

The owner's request (27 Nov 2026): look a word up in the list NodeTrail already has, without starting a session.

## What
- **API `GET /vocab/search?q=…&list=core-seed&limit=20`** returns `{status, total, results: [WordCard]}` from the loaded
  word list (3,663 words today). No database, no learner, no model call. `q` is 1–40 characters, NFC-normalised and
  compared case-insensitively.
- **Matching (pure function `app/vocabulary/search.py`), in this order:**
  1. the headword equals the query;
  2. the headword starts with the query;
  3. the headword contains the query (queries of 3 letters or more);
  4. the Vietnamese meaning contains the query as whole syllables **with its diacritics** ("bàn" finds "bàn", not "bán");
  5. only for a query typed without any diacritic: the Vietnamese meaning contains it as whole syllables once diacritics are removed
     ("ban" also finds "bàn", "bán", "bạn"), ranked last because it is the noisiest.
  Inside a group: easier level first, then alphabetical. `total` counts every match; `limit` caps the list (at most 50).
- **Web `/tu-dien`** ("Từ điển" in the nav): a search box; each result is the same word card as in practice (word, IPA
  where shown, part of speech, level, the English definition, the Vietnamese meaning, the example, listen). The list is a
  draft until a teacher checks a sample, so the page says "Bản nháp" and the imported words keep their labels
  ("ước lượng theo tần suất", "phiên âm tự động").

## What is not claimed
It searches only NodeTrail's word list, not a full dictionary: no other senses, no words outside NGSL/NAWL and the
authored words. A word with two parts of speech shows two cards.

## Tests
Unit tests for each matching rule and the ranking; an API test (search, empty query rejected, limit); Vitest for decoding;
Playwright: search a word on `/tu-dien` and see its card.
