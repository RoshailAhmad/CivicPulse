# Deliberate merge conflict

**File:** `backend/app/providers/triage/rules.py`, the `HIGH_WORDS` list.

- Roshail's branch (`feat/ci-cd`) added `"short circuit"` to the high-priority words.
- Mehak's branch (`docs/final-docs`) added `"open manhole"` at the same place.
- Both branches started from the same `dev` commit, so merging the second PR produced a
  conflict on those lines.

**Conflict markers (paste what Git showed):**

```
(paste the <<<<<<< / ======= / >>>>>>> block here)
```

**Resolution:** *(2 to 4 sentences, in your own words, on which version won and why.
For example: we kept both words, because each describes a real danger that should jump
the queue, and neither change made the other wrong.)*

**Screenshot:** `merge-conflict.png` (the conflict on GitHub, before resolving).
