/*
  AI Coach — shared normalization, fuzzy matching and intent scoring.

  Why this file exists: coach-chat.js and coach-knowledge.js used to route
  every message through hand-written regexes, first match wins. That only
  answers a sentence typed exactly the way the pattern's author imagined -
  "scroe", "wht am i god at" or a Persian/Arabic message that spells the
  same letter with a different (but equally correct) codepoint all missed
  and fell through to a generic reply, because equality has no notion of
  "close enough".

  This module does NOT replace the ~40 hand-written topic regexes in
  coach-knowledge*.js - those still work exactly as before and are tried
  first (an exact regex hit always scores 1.0, so behaviour for anyone who
  already asked the "expected" way is unchanged). It adds a second, fuzzy
  path on top of the SAME topic definitions: it parses each topic's
  regex.source into a plain keyword list once, then scores a normalized,
  tokenized query against every topic's keywords, and returns the single
  best-scoring intent instead of whichever `if` happened to run first.

  Four responsibilities:
    1. normalize()  - case, punctuation, diacritics, and the fa/ar letter-
                       shape variants that are the majority of "typos" in
                       those languages, not actual spelling mistakes.
    2. distance()    - bounded Damerau-Levenshtein edit distance.
    3. extractKeywords() - turn an existing topic regex into a keyword
                       list, so nobody has to hand-duplicate ~40 topics'
                       word lists in a second format.
    4. classify()    - score every candidate intent against a message and
                       return the winner AND the runner-up, so callers can
                       give an honest "did you mean X or Y" instead of
                       silently guessing or silently refusing.
*/
(function () {
  // ------------------------------------------------------------ normalize
  // Arabic-Indic and Extended (Persian) Arabic-Indic digits -> ASCII.
  const DIGIT_MAP = {
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4', '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
    '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4', '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
  };

  function normalize(text) {
    let s = String(text || '');
    s = s.toLowerCase();
    // Arabic diacritics (tashkeel/harakat) - purely pronunciation marks,
    // never meaningful for matching a typed question.
    s = s.replace(/[ً-ٰٟۖ-ۭ]/g, '');
    // Letter-shape variants that are really the same letter: Arabic yeh /
    // alef maksura -> Persian yeh, Arabic kaf -> Persian keh, teh marbuta
    // -> heh, and the hamza-bearing seats of alef/waw/yeh -> their bare
    // form (أ/إ/آ -> ا, ؤ -> و, ئ -> ی). A large share of "misspellings"
    // reported in fa/ar are just a different, equally correct codepoint
    // for the same letter - "انام" vs "أنام" ("I sleep") is one hamza,
    // not a typo.
    s = s.replace(/[يى]/g, 'ی').replace(/ك/g, 'ک').replace(/ة/g, 'ه');
    s = s.replace(/[أإآ]/g, 'ا').replace(/ؤ/g, 'و').replace(/ئ/g, 'ی');
    // Zero-width non-joiner: sometimes a real separator ("می‌روم"),
    // sometimes typed as a plain space by mistake. Folding it to a space
    // makes both spellings tokenize the same way.
    s = s.replace(/‌/g, ' ');
    s = s.replace(/[٠-٩۰-۹]/g, (d) => DIGIT_MAP[d] || d);
    // Strip punctuation/symbols, keep letters (any script), digits, space.
    s = s.replace(/[^\p{L}\p{N}\s]/gu, ' ');
    s = s.replace(/\s+/g, ' ').trim();
    return s;
  }

  function tokenize(text) {
    const n = normalize(text);
    return n ? n.split(' ').filter(Boolean) : [];
  }

  function isCJK(s) {
    return /[一-鿿]/.test(s);
  }

  // ------------------------------------------------------------ distance
  // Damerau-Levenshtein (adjacent transposition counts as one edit, which
  // matters a lot for typos like "scroe" -> "score"). Bounded to keep this
  // cheap even on a long pasted message; matching degrades to "not close"
  // beyond the bound rather than hanging.
  function distance(a, b) {
    const al = a.length, bl = b.length;
    if (a === b) return 0;
    if (al === 0) return bl;
    if (bl === 0) return al;
    if (al > 24 || bl > 24) return Math.max(al, bl); // not a typo, a different message

    const d = [];
    for (let i = 0; i <= al; i++) d[i] = [i];
    for (let j = 0; j <= bl; j++) d[0][j] = j;

    for (let i = 1; i <= al; i++) {
      for (let j = 1; j <= bl; j++) {
        const cost = a[i - 1] === b[j - 1] ? 0 : 1;
        let val = Math.min(
          d[i - 1][j] + 1,      // deletion
          d[i][j - 1] + 1,      // insertion
          d[i - 1][j - 1] + cost // substitution
        );
        if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
          val = Math.min(val, d[i - 2][j - 2] + cost); // transposition
        }
        d[i][j] = val;
      }
    }
    return d[al][bl];
  }

  /** 0..1, where 1 is identical. */
  function wordSimilarity(a, b) {
    if (a === b) return 1;
    const maxLen = Math.max(a.length, b.length);
    if (maxLen === 0) return 1;
    return 1 - distance(a, b) / maxLen;
  }

  // A flat similarity floor, picked empirically (see tests/coach_nlu_corpus
  // and the false-positive pairs recorded there) to sit strictly between
  // typo pairs that must match and unrelated-word pairs that must not:
  //   accept  scroe/score   0.80   sleeep/sleep  0.83   routine/routeen 0.71
  //   reject  scroe/scroll  0.67   thx/the       0.67
  // A length-scaled threshold looked appealing (longer words can plausibly
  // absorb more edits) but "routine"/"routeen" and "scroe"/"scroll" are
  // both a 2-edit gap on a 6-7 letter word - one desired, one not - so no
  // per-length curve separates them. A flat cutoff at 0.7 does, and as a
  // side effect it already requires short words (<=3 letters) to match
  // exactly, since even a single edit drops a 3-letter word below it -
  // which is correct anyway ("thx" is too short to safely fuzz).
  const FUZZY_FLOOR = 0.7;

  function wordMatchesToken(word, token) {
    if (!word || !token) return 0;
    if (word === token) return 1;
    if (isCJK(token) || isCJK(word)) {
      // CJK has no whitespace-delimited "words" and no typos in the Latin
      // sense - a token either appears as a substring or it does not.
      //
      // But the substring test has to know which side is which. A CJK
      // keyword is one long unbroken token ("shap因素是什么"), and an
      // unguarded symmetric `includes` made every such keyword a
      // wildcard for EVERY language: the query word "a" is inside
      // "shap", "far" is inside "在safari里能用吗", "i" is inside
      // "教练是真的ai吗". Each scored 0.9, so an English question about
      // nothing in this app - "how far is the moon?" - out-scored the
      // honest refusal and got a confident answer about browser support.
      // Measured before fixing: 4 of 9 plainly off-topic questions were
      // answered rather than declined.
      // CJK against CJK is the case this branch was written for, and it
      // is left exactly as it was. A shortest-side length guard was
      // tried here too and removed again: it cost 2.3 points of Chinese
      // recall (87.9% -> 85.6% over the 1992-case zh corpus) and caught
      // none of the off-topic answers, all of which came from the
      // mixed-script path below.
      if (isCJK(token) && isCJK(word)) {
        return word.includes(token) || token.includes(word) ? 0.9 : 0;
      }
      // One side is CJK, the other is Latin. The only honest match is
      // against a Latin fragment embedded in the CJK side - "shap" in
      // "shap因素是什么" - and it has to be the WHOLE fragment, so that a
      // stray letter cannot stand in for it.
      const cjkSide = isCJK(token) ? token : word;
      const latinSide = isCJK(token) ? word : token;
      if (latinSide.length < 3) return 0;
      return cjkSide
        .split(/[^0-9a-z]+/i)
        .some((fragment) => fragment.length >= 3 && fragment === latinSide) ? 0.9 : 0;
    }
    // Edit-distance similarity is noisy on short strings: Persian خوب
    // ("good") is one edit from خواب ("sleep") at 0.75 similarity - well
    // above FUZZY_FLOOR - and there is no flat threshold that accepts
    // "routine"/"routeen" (0.71) while rejecting that pair, because 0.75
    // sits on the wrong side of 0.71. Below five characters the fix is to
    // stop fuzzing rather than chase an unreachable threshold: exact
    // match only.
    if (Math.min(word.length, token.length) < 5) return 0;
    const sim = wordSimilarity(word, token);
    return sim >= FUZZY_FLOOR ? sim : 0;
  }

  // Short, extremely generic words that show up as a throwaway
  // alternative inside a larger disjunction (see extractKeywords below)
  // and would otherwise become a standalone "keyword" matching almost any
  // sentence that happens to contain them.
  const GENERIC_SINGLE_WORDS = new Set([
    'good', 'well', 'fine', 'bad', 'ok', 'okay', 'alright', 'normal',
    'nice', 'great', 'big', 'small', 'high', 'low', 'better', 'worse',
  ]);

  // ------------------------------------------------------- keyword mining
  // Pulls the literal alternatives out of an existing topic regex's
  // .source instead of asking every topic to also maintain a parallel
  // keyword list. Heuristic, not a full regex parser: entries that still
  // look like regex syntax after cleanup (lookaheads, character classes,
  // quantifiers) are dropped, on the theory that the ORIGINAL regex still
  // covers that exact case in classify() below - this only widens
  // coverage, it never narrows it.
  function extractKeywords(source) {
    if (!source) return [];
    // Nearly every topic ends its English group with a plural/gerund
    // suffix like "(?:s|es|ing)?". Splitting on "|" before removing this
    // whole unit turns its last alternative into a standalone piece -
    // "ing)?\b" - which cleans up into the bare keyword "ing", matching
    // almost any English word that ends in it. Strip the whole group
    // first so none of its parts are ever split out on their own.
    source = source.replace(/\(\?:[a-zA-Z|]+\)\?/g, '');
    // Position-anchored patterns (^...) mean "only at the start of the
    // message" - e.g. the greeting topic's "good (morning|evening)".
    // Fuzzy scoring has no notion of position, so treating its words as
    // ordinary keywords would make "what's a good morning routine"
    // register as a greeting. The exact regex still matches a real
    // greeting exactly as before; this only skips the fuzzy widening for
    // the handful of topics where widening would change the meaning.
    if (/^\^|\|\^/.test(source)) return [];
    const seen = new Set();
    const out = [];
    const add = (p) => {
      if (!p) return;
      if (/[\[\]{}*+.]/.test(p)) return; // still looks like regex syntax - skip
      const bare = p.replace(/\s+/g, '');
      // A single Chinese character is almost always too ambiguous to use
      // as a topic signal on its own (e.g. 困 alone can mean sleepy,
      // trapped, or tired) - same reasoning as the 3-letter floor for
      // Latin/fa/ar, just at CJK's own scale of one character less.
      const minLen = isCJK(p) ? 2 : 3;
      if (bare.length < minLen) return;
      const norm = normalize(p);
      if (!norm || seen.has(norm)) return;
      // A regex like /am i (doing )?(ok|okay|well|fine|good|alright)/
      // is one intent ("reassurance"), but naive splitting on "|" turns
      // its inner alternation into standalone keywords "good", "fine",
      // "bad" - generic enough to appear in almost any sentence. Multi-
      // word phrases ("good news", "good at") are unaffected: they still
      // require their OTHER word too, which is what keeps them specific.
      if (!norm.includes(' ') && GENERIC_SINGLE_WORDS.has(norm)) return;
      seen.add(norm);
      out.push(norm);
    };
    source.split('|').forEach((piece) => {
      const cleaned = piece
        .replace(/\\b/g, '')
        .replace(/\(\?:/g, '')
        .replace(/[()]/g, '')
        .replace(/[?^$]/g, '')
        .replace(/\\(.)/g, '$1')
        .trim();
      if (!cleaned) return;
      // "doom.?scroll" / "multi.tasking" / "work.life" - a literal dot
      // (optionally followed by "?") is used throughout these patterns as
      // "any separator or none". The concatenated form ("doomscroll") is
      // usually how people actually type it, so emit that AND the spaced
      // form ("doom scroll") rather than picking one and guessing wrong.
      if (/\w\.\??\w/.test(cleaned)) {
        add(cleaned.replace(/(\w)\.\??(\w)/g, '$1$2'));
        add(cleaned.replace(/(\w)\.\??(\w)/g, '$1 $2'));
        return;
      }
      add(cleaned);
    });
    return out;
  }

  // ------------------------------------------------------------- scoring
  /** Best alignment score of a (possibly multi-word) keyword phrase against
   *  the query's tokens. */
  function phraseScore(queryTokens, keywordNormalized) {
    const kTokens = keywordNormalized.split(' ').filter(Boolean);
    if (!kTokens.length) return 0;
    if (kTokens.length === 1) {
      let best = 0;
      for (const q of queryTokens) best = Math.max(best, wordMatchesToken(q, kTokens[0]));
      return best;
    }
    let matched = 0;
    let sum = 0;
    for (const kt of kTokens) {
      let best = 0;
      for (const q of queryTokens) best = Math.max(best, wordMatchesToken(q, kt));
      if (best > 0) { matched += 1; sum += best; }
    }
    const coverage = matched / kTokens.length;
    if (coverage < 0.6) return 0; // most of the phrase absent - not this intent
    return (sum / kTokens.length) * coverage;
  }

  /**
   * intents: [{ key, pattern?: RegExp, keywords: string[] (normalized),
   *             weight?: number }]
   * Returns { match, score, runnerUp, ranked } where `match` is null if
   * nothing cleared the threshold - callers use `runnerUp`/`ranked` for an
   * honest "did you mean" instead of a bare refusal.
   */
  /* The lowest score a regex hit can be worth. Equal to classify()'s
     default acceptance threshold on purpose: a pattern that matched is
     always still a match, however little of the message it covered. */
  const REGEX_HIT_FLOOR = 0.62;

  /* The same idea applied to keywords, but gentler. A keyword match is
     already a similarity rather than a yes/no, so multiplying it by a
     floor as low as the regex one pushed genuine matches under the
     threshold: "how do i stop doomscroling" is a typo'd 26-character
     question answered by a 13-character keyword, and at 0.62 it stopped
     being answered at all. 0.75 still separates a small word claiming a
     long sentence from a keyword that accounts for most of it. */
  const KEYWORD_COVERAGE_FLOOR = 0.75;

  function classify(text, intents, opts) {
    const threshold = (opts && opts.threshold) || 0.62;
    const raw = String(text || '');
    const qTokens = tokenize(raw);
    const ranked = (intents || []).map((intent) => {
      /* A regex hit used to score a flat 1, which meant a broad topic
         that matched one word beat a narrow topic that matched the whole
         phrase. "ctach up on sleep" went to the general `sleep` topic on
         the strength of the bare word "sleep" (1.000) over `sleep_debt`
         at 0.950, and "overseleping on weekend" went to
         `weekend_pattern` over sleep_debt at 0.972. Half of the
         matcher's measured failures were that shape.

         So a regex hit is now scored by how much of the message it
         actually explains. The floor is the acceptance threshold
         itself, so nothing that matched before drops below it - a hit
         is still always a match - but a hit covering the whole question
         still reaches 1, and one covering a fifth of it no longer
         outranks a near-perfect read of the whole thing. */
      let regexHit = 0;
      if (intent.pattern) {
        const hit = raw.match(intent.pattern);
        if (hit) {
          const covered = hit[0].length / Math.max(raw.trim().length, 1);
          regexHit = REGEX_HIT_FLOOR
            + (1 - REGEX_HIT_FLOOR) * Math.min(1, covered);
        }
      }
      /* Keywords are scored the same way, and for the same reason: the
         bare keyword "sleep" is a perfect 1 against "ctach up on sleep"
         while explaining under a third of it, which is how the general
         sleep topic kept beating sleep_debt. Weighting by how much of
         the question the keyword accounts for leaves a short question
         answered by a short keyword untouched ("sleep" against "sleep"
         still covers everything) and only demotes a small word claiming
         a long sentence. */
      let kwScore = 0;
      const qLength = Math.max(raw.trim().length, 1);
      for (const kw of intent.keywords || []) {
        const similarity = phraseScore(qTokens, kw);
        if (!similarity) continue;
        const covered = Math.min(1, String(kw).length / qLength);
        const scaled = similarity
          * (KEYWORD_COVERAGE_FLOOR + (1 - KEYWORD_COVERAGE_FLOOR) * covered);
        kwScore = Math.max(kwScore, scaled);
      }
      const weight = typeof intent.weight === 'number' ? intent.weight : 0;
      const score = Math.max(regexHit, kwScore) + weight * 0.001;
      return { intent, score };
    }).sort((a, b) => b.score - a.score);

    const top = ranked[0];
    const match = top && top.score >= threshold ? top.intent : null;
    return {
      match,
      score: top ? top.score : 0,
      runnerUp: ranked[1] ? ranked[1].intent : null,
      ranked,
    };
  }

  window.DWCoachNLU = {
    normalize, tokenize, distance, wordSimilarity,
    extractKeywords, phraseScore, classify,
  };
})();
