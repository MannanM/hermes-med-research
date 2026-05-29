# PubMed Acronym False Positives — Observed Patterns

From the 2026-05-26 MCAS roundup, a 7-day PubMed query for `(MCAS OR mast cell activation syndrome OR mastocytosis)` returned 5 articles — only 1 of 5 was directly MCAS-relevant (80% false positives).

## How PubMed Matches

PubMed translates "MCAS" to `"MCAS"[All Fields]`, which is **case-insensitive text matching** across the entire article record (title, abstract, keywords, MeSH terms). This catches:

| False match | Domain | How it appears |
|---|---|---|
| `mCAs` | Cancer genomics | "mosaic chromosomal alterations" — abbreviated as `mCAs` |
| `MCA` | Respiratory physiology | "minimal cross-sectional area" — abbreviated as `MCA` |
| `MCA` | Materials science | Rare acronym overload in unrelated chemistry/physics papers |

## Concrete Examples from 2026-05-19–2026-05-25

| PMID | Query Match Reason | Topically Relevant? |
|---|---|---|
| 42156185 | Genuine MCAS paper (REMA score, mastocytosis, clonal mast cell disease) | ✅ Yes |
| 42156563 | Matched "mCAs" (mosaic chromosomal alterations) in blood cancer genetics | ❌ No |
| 42160037 | Matched "MCA" (minimal cross-sectional area) in nasal physiology study | ❌ No |
| 42160028 | Matched "MCA" (minimal cross-sectional area) in perovskite solar cells paper | ❌ No |
| 42168198 | Matched "mCAs" (mosaic chromosomal alterations) in clonal hematopoiesis | ❌ No |

## MCAS Relevance Markers (for QC Screening)

Check title, abstract, and keywords for any of these to confirm true MCAS relevance:

- `mast cell` (appears in most genuine papers)
- `mastocytosis`
- `tryptase`
- `KIT` (especially `KIT D816V`)
- `anaphylaxis`
- `urticaria`
- `antihistamine` or `anti-histamine`
- `cromolyn`
- `omalizumab` / `Xolair`
- `mast cell activation`
- `mediator release`
- `clonal mast`

## Recommended Pattern

For future MCAS runs: keep the broad query for full recall, but tag each article as `[RELEVANT]` or `[FALSE POSITIVE]` after ingest using the markers above. Downstream skills (research-processor, research-post-writer) should skip `[FALSE POSITIVE]` articles.

---

## Update — 2026-05-27 Run (Single-Day Query)

A single-day PubMed query (`2026-05-26`) with both `pdat` and `edat` returned **3 articles, all 3 relevant** (0% false positive rate). This contrasts with the 7-day backfill's 80% FP rate.

| Query | PMIDs Found | False Positives |
|---|---|---|
| `pdat` (2026/05/26) | 41604606 | 0 |
| `edat` (2026/05/26) | 42186391, 42184879 | 0 |
| **Merged (deduplicated)** | **3 total** | **0 (0%)** |

### Articles (all MCAS-relevant)

| PMID | Topic | Query Match |
|---|---|---|
| 41604606 | Avapritinib in advanced systemic mastocytosis (PATHFINDER 4yr) | `pdat` — published 2026-01-28 but matched May 26 pub date query (re-indexed) |
| 42184879 | Depression in mastocytosis — neglected comorbidity review | `edat` — published 2026-05-24, entered May 26 |
| 42186391 | Dysautonomia and hypertension in hEDS/HSD (mentions mast cell activation) | `edat` — published 2026-05-21, entered May 26 |

### Observation: `pdat` vs `edat` Divergence

Article 41604606 (published Jan 2026) appeared in the `pdat` query for May 26, meaning PubMed re-indexed or updated its publication date. The `edat` queries caught articles that were newly entered into PubMed on May 26 but published days earlier. This confirms that **`pdat` and `edat` should always be run in tandem** — they capture different subsets of articles.

### Observation: Single-Day vs Multi-Day False Positive Rate

The 0% FP rate on a single day vs 80% on a 7-day range suggests that false positive rate scales with query breadth. Single-day queries are lower-volume and more precisely scoped. The QC screening is most critical for wide multi-day backfills.

---

## Update — 2026-05-28 MECFS Run (QC Substring Bug Discovery)

A single-day `edat` query for MECFS (`REPORT_DATE=2026-05-27`) returned **5 articles — 4 relevant, 1 false positive** (20% FP rate). All were found via `edat` (entry date) with zero `pdat` results.

| Query | PMIDs Found |
|---|---|
| `pdat` (2026/05/27) | 0 |
| `edat` (2026/05/27) | 42196466, 42196410, 42196290, 42194915, 42190845 |

### Articles

| PMID | Title | Date Dir | QC Tag |
|---|---|---|---|
| 42196290 | *Human Endogenous Retroviruses in Myalgic Encephalomyelitis/Chronic Fatigue Syndrome* (Int J Mol Sci) | 2026-05-12 | ✅ RELEVANT |
| 42196410 | *Toward a Molecular Reclassification of ME/CFS* (Int J Mol Sci) | 2026-05-15 | ✅ RELEVANT |
| 42196466 | *Immunophenotyping of Monocytes and Dendritic Cells in CFS and Long COVID* (Int J Mol Sci) | 2026-05-17 | ✅ RELEVANT |
| 42190845 | *Shared genetic risk between functional somatic syndromes and immune-mediated diseases* (Brain Behav Immun) | 2026-05-25 | ✅ RELEVANT |
| 42194915 | *When Dryness Extends to the Brain: Sjögren's Disease* (J Clin Med) | 2026-05-20 | ❌ FALSE POSITIVE |

### Critical Bug: Substring `cfs` Matches Inside File Paths

The initial QC used `'cfs' in text.lower()` — naive substring matching. This caused **PMID 42194915 (Sjögren's disease)** to be incorrectly tagged RELEVANT because `cfs` matched inside the string `articles-MECFS` in the Artifact Metadata section's file path.

Fix applied to the skill:
1. Use regex word boundaries: `\bcfs\b` instead of substring `'cfs' in text`
2. Strip the `## Artifact Metadata` section from the `.md` file before QC matching (it contains REPORT_TYPE path strings)
3. Pass the `pmid` explicitly to scope QC to that article's files

### How the Sjögren's FP Matched PubMed
The MECFS PubMed query `(ME/CFS OR myalgic encephalomyelitis OR chronic fatigue syndrome)` matched this article because the abstract mentions "chronic fatigue" as a symptom of Sjögren's disease — the word "fatigue" (not "chronic fatigue syndrome") triggered the match. This is a common-word false positive indistinguishable from legitimate "fatigue" mentions in ME/CFS papers at the query level. QC markers must disambiguate.

### Statistical Note: Three Consecutive MECFS Runs

| Run Date | Range | Articles | Relevant | FPs | FP Rate |
|---|---|---|---|---|---|
| 2026-05-25 | 2026-05-25 | 2 | 1 | 1 | 50% |
| 2026-05-27 | 2026-05-26 | 2 | 1 | 1 | 50% |
| 2026-05-28 | 2026-05-27 | 5 | 4 | 1 | 20% |
| **Total** | 3 runs | 9 | 6 | 3 | **33%** |

The MECFS FP rate (33% overall) is driven by common-word matches ("fatigue" in unrelated conditions) rather than acronym overload. This is lower than MCAS (80% FP) but still substantial enough to warrant QC on every run.

A single-day query for MECFS (`REPORT_DATE=2026-05-26`) returned **2 articles — 1 relevant, 1 false positive** (50% FP rate).

| Query | PMIDs Found |
|---|---|
| `pdat` (2026/05/26) | 42055743 |
| `edat` (2026/05/26) | 42187063 |

### Articles

| PMID | Title | QC Tag |
|---|---|---|
| 42055743 | *Underuse of Pharmacologic Therapies for ME/CFS Before Specialist Evaluation* (Ann Fam Med) | ✅ RELEVANT |
| 42187063 | *Hypermobility and chronic pain in adolescents* (Pain) — found via `edat`, published 2026-05-15 | ❌ FALSE POSITIVE |

### How the False Positive Matched
The MECFS query includes `chronic fatigue syndrome`. PMID 42187063 is about chronic pain in adolescents with hypermobility. The abstract mentions "increased fatigue" as a secondary symptom in the CP+HD cohort. PubMed's All Fields search matched the word "fatigue" in the abstract. The article has nothing to do with ME/CFS.

### Key Insight: Common-Word FPs Differ from Acronym FPs

| FP Type | Example | Mechanism | Difficulty filtering |
|---|---|---|---|
| **Acronym overload** | MCAS → mCAs | Case-insensitive matching of short strings | Hard — acronyms can't be narrowed without losing real hits |
| **Common-word match** | "fatigue" in MECFS → unrelated pain paper | Symptom words appear in many contexts | Moderate — QC markers (ME/CFS, PEM, postexertional) are more specific than the query itself |
| **Tangential condition overlap** | POTS → general dysautonomia | Overlapping terminology | Low — article may be peripherally relevant |

### Recommendation for MECFS QC
- Use specific disease markers: `me/cfs`, `myalgic encephalomyelitis`, `postexertional malaise`, `orthostatic intolerance`
- The base query term `fatigue` alone is insufficient — "fatigue" is a symptom of hundreds of conditions
- `edat`-found articles are higher-risk for FPs since they may be older articles with tangential keyword overlap
