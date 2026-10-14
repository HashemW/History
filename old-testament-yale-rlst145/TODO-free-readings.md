# Free readings: progress notes (pick up here)

**Goal:** give every non-Bible reading a **free, legal** online link, with nothing to buy.
Research done 2026-10-14. The lecture pages are only partly updated (see "Remaining steps").

## ✅ Free to borrow on the Internet Archive (free account; each copy confirmed borrowable)

| Reading | Lectures | Free copy (archive.org/details/…) | Pages |
|---|---|---|---|
| *The Jewish Study Bible* (2004 ed., same as syllabus) | almost all | [jewishstudybible0000unse_x6n0](https://archive.org/details/jewishstudybible0000unse_x6n0) | as listed per lecture |
| Pritchard, *The Ancient Near East* Vol. 1 (1958) | 2–3 (pp. 28–75), 10–11 (pp. 133–166) | [ancientneareasta00prit](https://archive.org/details/ancientneareasta00prit) (backup: ancientneareasta0000vari) | |
| Kaufmann, *The Religion of Israel* (1972) | 2–3 | [religionofisrael0000kauf_j7j0](https://archive.org/details/religionofisrael0000kauf_j7j0) | 21–121 |
| Trible, "Depatriarchalizing in Biblical Interpretation" (reprint) | 4–5 | [jewishwomannewpe0000kolt](https://archive.org/details/jewishwomannewpe0000kolt/page/217/mode/2up) (Koltun, *The Jewish Woman*, 1976) | 217–240 |
| ABD, "Interpretation, History of" | 12 | [anchorbibledicti0003unse_b2a9](https://archive.org/details/anchorbibledicti0003unse_b2a9/page/424/mode/2up) (vol. 3) | 424–427, 434–436 |
| ABD, "Apocalypses" | 24 | [anchorbibledicti0001unse_l6c5](https://archive.org/details/anchorbibledicti0001unse_l6c5/page/279/mode/2up) (vol. 1) | 279–288 |
| Reis, "Spoiled Child" in *Reading the Lines* (2002) | 12 | [readinglinesfres0000reis](https://archive.org/details/readinglinesfres0000reis) | |
| Wilson, "Biblical Prophecy," *Encyclopedia of Religion* vol. 12 | 15 | [encyclopediaofre12elia](https://archive.org/details/encyclopediaofre12elia/page/14/mode/2up) | 14–23 |
| Milgrom, "Israel's Sanctuary: The Priestly 'Picture of Dorian Gray'" | 9 | **Probably** reprinted in *Studies in Cultic Theology and Terminology* (1983), [bwb_S0-BYL-636](https://archive.org/details/bwb_S0-BYL-636), pp. 75–84 (table of contents **not yet confirmed**). Confirmed fallback: Milgrom, *Leviticus 1–16* (1991), [leviticus11600jaco](https://archive.org/details/leviticus11600jaco/page/260/mode/2up), p. 260 | |

## ✅ Free online, public domain or open (for the Pritchard myths and laws)

- Sumerian Flood Story ("The Deluge"): https://etcsl.orinst.ox.ac.uk/section1/tr174.htm
- *Enuma Elish* ("Creation Epic"), L. W. King 1902: https://sacred-texts.com/ane/enuma.htm
- *Gilgamesh*: R. Campbell Thompson 1928, https://sacred-texts.com/ane/eog/index.htm ; Jastrow & Clay 1920, https://www.gutenberg.org/ebooks/11000
- *Code of Hammurabi* (King): https://avalon.law.yale.edu/ancient/hamframe.asp
- Note: the build script's Python check wrongly dropped the two sacred-texts links (the site blocks Python's default user agent, but curl with a browser user agent gets HTTP 200). Re-add them.

## 🔍 Still checking (leads found, borrow status not yet confirmed)

- Auerbach, "Odysseus' Scar" (L6–7): reprinted in *Homer: A Collection of Critical Essays* (1962), p. 19: `homercollectiono0000stei`, `homer0000unse_x3d7`, `bwb_S0-EFZ-407`; in *Perspectives on Fiction* (1968), p. 3: `perspectivesonfi00cald`, `perspectivesonfi0000unse_p4k1`; and *Mimesis* 2003 ed.: `mimesisrepresent00auer_0`.
- Original JAAR 41 (1973) scan with Trible at pp. 30–48: `journalofamerica0041unse`.
- Full-text search results for the remaining readings are in `../tools/fts-results.txt`.

## ❌ No free legal copy found yet

All are print-disabled-only on the Internet Archive, or paywalled. Fallback for every one of them: **a free public library card** (Libby/Hoopla e-books, or free Interlibrary Loan).

- Habel, *Literary Criticism of the OT* (L4–5, pp. 1–42), a regular reading
- Sternberg, *The Poetics of Biblical Narrative* (L13–14, pp. 186–222), a regular reading. Lead: Perry & Sternberg, "The King through Ironic Eyes," *Poetics Today* 7.2 (1986)
- Alter, *The Art of Biblical Narrative* (L6–7, section). Leads: ch. 1 began as "A Literary Approach to the Bible," *Commentary* (Dec 1975); ch. 3 as "Biblical Type-Scenes…," *Critical Inquiry* 5.2 (1978)
- Boyarin, *Carnal Israel* (L4–5, section). The UC Press e-book is UC-only. Lead: earlier article "Behold Israel According to the Flesh," *Yale Journal of Criticism* 5.2 (1992)
- Pagels, *Adam, Eve, and the Serpent* (L4–5, section)
- Greenstein & Preminger, *The Hebrew Bible in Literary Criticism* (L6–7, section)
- *Out of the Garden* essays by Goldstein, Levinson and Ozick (optional)
- ANET law collections (L10–11, "consult"). Lead: check whether the borrowable Pritchard *ANE* Vol. II (`ancientneareastv0000unse`) or the 1969 *Supplement* (`ancientneareasts0000jame_a9q1`) contain Ur-Nammu, Lipit-Ishtar, the Middle Assyrian laws or the Hittite laws

**Do not link:** "folkscanomy," "pdfdrive" or "opensource" uploads of copyrighted books (JSB, ABD, ANET); these are unauthorized copies.

## Remaining steps (for the next session)

1. Finish the 🔍 checks above.
2. In `tools/build.py`, replace `SOURCES` with per-reading entries that deep-link to the assigned page (`https://archive.org/details/<id>/page/<n>/mode/2up`) and re-add the sacred-texts links.
3. Add a "Free readings" page linked from the course README, rebuild, and push.

**Rebuild:** download the Yale pages to a scratch folder (`curl -sL https://oyc.yale.edu/religious-studies/rlst-145` plus `/lecture-1` … `/lecture-24` and `/exam-1`, saved as `course.html`, `lecture-N.html`, `exam-1.html`), then run `python -X utf8 tools/build.py <scratch_dir> <repo_root>`.
**Useful APIs:** `https://archive.org/metadata/<id>` (borrowable if its collection list contains `inlibrary`); full-text search: `https://archive.org/services/search/beta/page_production/?service_backend=fts&user_query=...`
