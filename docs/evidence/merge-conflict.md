# Deliberate merge conflict

**File:** `backend/app/providers/triage/rules.py`, the `HIGH_WORDS` list.

- Roshail's branch (`feat/ci-cd`) added `"short circuit"` to the high-priority words.
- Mehak's branch (`docs/final-docs`) added `"open manhole"` at the same place.
- Both branches started from the same `dev` commit, so merging the second PR produced a
  conflict on those lines.

**Conflict markers (paste what Git showed):**

```
   <<<<<<< docs/final-docs
       "open manhole",
   =======
       "short circuit",
   >>>>>>> dev
```

**Resolution:** *We kept both words. Short circuits and open manholes are both real dangers that should jump the queue, and neither change made the other wrong. Keeping one would have silently thrown away a partner's valid fix.*

**Screenshot:** `merge-conflict.png` (the conflict on GitHub, before resolving).
