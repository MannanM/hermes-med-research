---
name: research-processor
description: "Iterate through date-specific research directories, generate plain-language summaries for laypersons, and update or create treatment tracking files in workspace/treatment-{REPORT_TYPE}/."
version: 3.1.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [research, treatment, tracking, summarization, consumer-health]
    related_skills: [research-roundup, mecfs-social-roundup]
---

# Research Processor

Process ingested research artifacts in `/opt/data/profiles/med-research/workspace/articles-{REPORT_TYPE}/{date}/` for a specific day or date range. For each article found, the skill generates a plain-language summary for a college-educated consumer without a medical background, saves it locally, and updates or creates tracking profiles in `workspace/treatment-{REPORT_TYPE}/` for any discussed therapies.

---

## Prerequisites

These variables must be available — they're passed by the cron job prompt or caller:

| Variable | Purpose |
|---|---|
| `REPORT_TYPE` | Controls which article and treatment directories to scan (e.g., MECFS, MCAS) |
| `REPORT_DATE_FROM` | Start of date range (YYYY-MM-DD) |
| `REPORT_DATE_TO` | End of date range (YYYY-MM-DD) |

---

## When to Use

- After running the `research-roundup` ingestion skill
- When requested to "process the literature from [Date/Range] for treatment updates"
- To backfill or update plain-language summaries and treatment files for historical dates

---

## Processing Workflow

Given a target date or date range (e.g., `2026-01-01` to `2026-01-03`):

### No-Op Guard: Check If Any Articles Exist

Before doing any work, check if the date range has any article directories:

```bash
for d in $(seq 0 $(( ($(date -d "$REPORT_DATE_TO" +%s) - $(date -d "$REPORT_DATE_FROM" +%s)) / 86400 ))); do
    date_dir=$(date -d "$REPORT_DATE_FROM + $d days" +%Y-%m-%d)
    dir="workspace/articles-${REPORT_TYPE}/${date_dir}"
    if [ -d "$dir" ] && [ "$(ls -A "$dir" 2>/dev/null)" ]; then
        has_articles=true
        break
    fi
done

if [ "$has_articles" != true ]; then
    echo "No articles found for ${REPORT_DATE_FROM} to ${REPORT_DATE_TO} — skipping."
    exit 0
fi
```

If no article directories exist for the range (or they're all empty), exit immediately and do nothing.

### Cron Tip: Don't Hunt for Variables

**You're in a cron session where `memory()` and `session_search()` are disabled** — they will fail silently and waste 2+ tool calls. The `REPORT_TYPE`, `REPORT_DATE_FROM`, and `REPORT_DATE_TO` are provided to you by the cron job prompt. Use them directly from context — don't try to look them up.

### Efficiency Rules (Reduce Tool Calls)

These rules can reduce a typical run from 30+ messages and 22+ tool calls down to ~15 messages and ~10 tool calls.

### 1. Skip Already-Summarized Articles First

Before reading any article content, **check which articles already have summaries** with a single terminal command:

```bash
ls workspace/articles-${REPORT_TYPE}/*/*-summary.md 2>/dev/null
```

Then cross-reference against the article `.md` files. Only read articles that lack a `{pmid}-summary.md`.

### 2. Batch Read Files in Fewer Calls

**Do NOT read metadata and full text in separate sequential calls.** Read them together using one of these strategies:

#### Strategy A: execute_code batch read (preferred — single tool call)

```python
# Use this pattern in execute_code to batch-read all articles in one call
from hermes_tools import read_file
articles = []
for pmid in pmids_to_process:
    meta = read_file(f"workspace/articles-{REPORT_TYPE}/{date}/{pmid}.md")
    text = read_file(f"workspace/articles-{REPORT_TYPE}/{date}/{pmid}-full.txt")
    articles.append({"pmid": pmid, "meta": meta["content"], "text": text["content"]})
```

This keeps intermediate file contents out of your context and processes all articles in a single agent turn.

#### PITFALL: execute_code read_file dedup crash

The `execute_code` environment's `read_file` has a **dedup mechanism**: if a file was already read with the regular `read_file` tool earlier in the same conversation, the execute_code version returns `{'status': 'unchanged', 'content_returned': False}` instead of the actual content, causing a `KeyError: 'content'` crash.

**Fallback approaches when this happens:**

1. **Plan reads upfront** — read all files you'll need with the regular `read_file` tool *before* entering execute_code, then pass content through the code string.
2. **Use absolute paths** — `from hermes_tools import terminal` and use `cat` inside execute_code to extract content:
   ```python
   from hermes_tools import terminal
   result = terminal(f"head -50 /opt/data/profiles/med-research/workspace/articles-{REPORT_TYPE}/{date}/{pmid}-full.txt")
   text = result["output"]
   ```
3. **Skip execute_code for batch reading** when you have >10 articles; read metadata with the regular `read_file` tool in groups of 5 via parallel calls, reading only the first 20 lines of each full-text file to determine relevance.
4. **Use the regular `read_file` serially** — more tool calls but more reliable. The efficiency trade-off is acceptable if the dedup issue would crash your batch script.

### 3. Check Treatment Files with search_files, Not Read All

Do NOT `read_file()` every existing treatment profile to see if a study is already referenced. Instead:

```bash
# Single grep to check if a PMID already appears in any treatment file
grep -l "42055743" workspace/treatment-${REPORT_TYPE}/*.md 2>/dev/null
```

Or use `search_files(pattern="PMID 42055743", path="workspace/treatment-{REPORT_TYPE}", file_glob="*.md", output_mode="files_only")`.

Only read a treatment file if you actually need to append new content to it.

### 4. Skip Todo List Overhead

**Do NOT use the `todo` tool** in cron context. Todos provide no value in a non-interactive session and add 4+ extra tool calls (create, update, update, final update). Instead, track progress in your own reasoning.

### 5. Skip Redundant Verification

**Do NOT verify written files with another `ls` or `terminal` call.** The `write_file` tool returns `"bytes_written": N` on success — that's sufficient confirmation. Verifying adds an unnecessary tool call after every write batch.

### 6. Compress the Final Report

Write the final summary directly — no need for intermediate "let me now do X" messages between every action. Plan the full sequences of reads, writes, and checks before executing them.

### Handle Off-Topic Articles Efficiently

Many articles in `articles-{REPORT_TYPE}/` may be only tangentially related or completely irrelevant (e.g., solar cell research, battery chemistry, non-connective-tissue cancers). **Do not spend equal effort on these.** Use a tiered approach:

1. **Tier 1 — Directly relevant** (EDS/hypermobility, connective tissue, dysautonomia, or specific treatments): Full summary with Overview, Key Findings, and "What This Means" section.
2. **Tier 2 — Marginally relevant** (orthopedic surgery, joint repair techniques, general pain management): Moderate summary — connect findings to hypermobility where possible.
3. **Tier 3 — Not relevant** (materials science, non-connective-tissue cancers, chemistry, physics, unrelated engineering): Write a one-paragraph placeholder noting the topic and stating it's not relevant. Takes 15 seconds instead of 2 minutes.

To quickly classify, skim the article title (from the `.md` metadata file's first line) — this is usually enough to determine the tier.

### Prioritize Processing Order

When there are many articles (15+), process them in this order:
1. First: All Tier 1 (directly HYPER-relevant) articles
2. Second: Tier 2 (marginally relevant) articles  
3. Last: Tier 3 (not relevant) — batch these with minimal summaries

This ensures the most valuable outputs are generated first and the final report focuses on meaningful findings.

### When Articles Are Found

**Apply the Efficiency Rules above (skip memory, batch reads, no todos, no verification).** Here's the optimized workflow:

1. **Skip Already-Summarized:** Run `ls workspace/articles-${REPORT_TYPE}/*/*-summary.md 2>/dev/null` to see which articles already have summaries. Only process articles missing a summary.

2. **Batch-Read Article Data:** Use `execute_code` with `from hermes_tools import read_file` to read metadata + full text for all unsummarized articles in **a single tool call**. This keeps 6+ intermediate reads out of your context.

3. **Generate Layperson Summary:** Write a plain-language summary and save to `workspace/articles-{REPORT_TYPE}/{date}/{pmid}-summary.md`.

4. **Identify Treatments:** Scan the texts for any therapeutic interventions.

5. **Check Treatment Files via grep, not read:** Run `grep -l "PMID" workspace/treatment-${REPORT_TYPE}/*.md 2>/dev/null` to see if this PMID is already referenced in any treatment file. Only read a treatment file if you need to append new content.

6. **Update/Create Treatment Profiles:**
   - If the treatment profile exists and the PMID isn't already there, append new findings.
   - If it does not exist, create it using the standard treatment template.
   - Update the status and evidence levels in the profile's tracking table.

---

## Step 1: Article Summary Format (`{pmid}-summary.md`)

Save the generated layperson summary in the same date folder as the raw article:
`workspace/articles-{REPORT_TYPE}/{date}/{pmid}-summary.md`

### Summary Template

```markdown
# Plain Language Summary: {{Study Title}}

> **Original Study:** [PMID {{pmid}}](https://pubmed.ncbi.nlm.nih.gov/{{pmid}}/) | **Published:** {{date}}
> **Local Resources:** [Metadata](./{{pmid}}.md) | [Full Text](./{{pmid}}-full.txt)

---

## Overview
A 1-2 paragraph description of what the researchers studied and why, written for a college-educated reader without a medical background. Avoid dense academic jargon (e.g., translate "upregulation of pro-inflammatory cytokines" to "an increase in proteins that trigger inflammation").

## Key Findings
- **Finding 1:** Clear, simple explanation of a core result.
- **Finding 2:** Clear, simple explanation of a core result.
- **Finding 3:** Any noted limitations (e.g., "This was a small pilot study of only 20 people...").

## What This Means for {REPORT_TYPE} Patients
Explain the practical relevance. Does this change treatment choices, offer diagnostic hope, or is it purely early-stage laboratory science?

## Investigated Treatments / Interventions
List any specific treatments evaluated or discussed in this study (e.g., Coenzyme Q10, Low-Dose Naltrexone, pacing).
```

---

## Step 2: Treatment Profile Schema

Map treatments mentioned in the study to their standardized filenames in `workspace/treatment-{REPORT_TYPE}/{treatment-name}.md`.

### Normalization Mapping Examples
- Low Dose Naltrexone/LDN → `low-dose-naltrexone.md`
- Metformin → `metformin.md`
- Coenzyme Q10/CoQ10 → `coq10.md`
- Stellate Ganglion Block/SGB → `stellate-ganglion-block.md`

### Creating a New Treatment Profile Template

```markdown
# {{Treatment Name}} for {REPORT_TYPE}

> Compiled: YYYY-MM-DD
> **Disclaimer:** This is not medical advice. Consult a healthcare professional before trying any treatment.

---

## Overview

2-3 paragraphs explaining what the treatment is, its primary FDA-approved use, and why it is being researched or utilized off-label for {REPORT_TYPE}.

---

## Current Status

| Aspect | Status |
|--------|--------|
| Evidence level | {{e.g., Single case report, Pilot study, Anecdotal, RCT, Meta-analysis}} |
| FDA approved for {REPORT_TYPE} | ❌ No / ⚠️ Off-label / ✅ Yes |
| Off-label use | {{Common / Rare / Experimental}} |
| Key risks | {{Primary safety concerns or side effects}} |
| Community interest | {{Low / Moderate / High}} |

---

## Scientific Findings

### Update — {{Publication Date}}
**Study:** *{{Title}}* (PMID: [{{pmid}}](https://pubmed.ncbi.nlm.nih.gov/{{pmid}}/))
**Local Summary:** [Layperson Summary](../articles-{REPORT_TYPE}/{{date}}/{{pmid}}-summary.md)

**Findings:**
- Bullet 1 detailing the study's specific findings on efficacy, dosage, or mechanism.
- Bullet 2 detailing safety, tolerability, or adverse events noted.

---

## Sources
- [PMID {{pmid}}](https://pubmed.ncbi.nlm.nih.gov/{{pmid}}/) - {{Title}}
```

### Updating an Existing Profile

When the profile file already exists in `workspace/treatment-{REPORT_TYPE}/`, do not overwrite it. **Append** the new findings under the `## Scientific Findings` section, and revise the **Current Status** table values (such as evidence level or risks) if the new study changes the consensus:

```markdown
### Update — {{Publication Date}}
**Study:** *{{Title}}* (PMID: [{{pmid}}](https://pubmed.ncbi.nlm.nih.gov/{{pmid}}/))
**Local Summary:** [Layperson Summary](../articles-{REPORT_TYPE}/{{date}}/{{pmid}}-summary.md)

**Findings:**
- {{Study-specific details...}}
```

---

## Step 3: Scripted Processing Orchestration

The following Python script helper handles directory navigation over single days or ranges, reads files, and sets up environment variables for LLM or agent processing:

```python
import os
import sys
from datetime import datetime, timedelta

REPORT_TYPE = os.environ.get("REPORT_TYPE", "UNKNOWN")

def get_date_range(start_str, end_str=None):
    start = datetime.strptime(start_str, "%Y-%m-%d")
    if not end_str:
        return [start_str]
    end = datetime.strptime(end_str, "%Y-%m-%d")
    delta = end - start
    return [(start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(delta.days + 1)]

def scan_articles(start_date, end_date=None):
    dates = get_date_range(start_date, end_date)
    articles_to_process = []

    for d in dates:
        dir_path = f"workspace/articles-{REPORT_TYPE}/{d}"
        if not os.path.exists(dir_path):
            continue

        files = os.listdir(dir_path)
        pmids = set([f.split('.')[0] for f in files if f.endswith('.md') and not f.endswith('-summary.md')])

        for pmid in pmids:
            articles_to_process.append({
                "date": d,
                "pmid": pmid,
                "meta_path": f"{dir_path}/{pmid}.md",
                "text_path": f"{dir_path}/{pmid}-full.txt",
                "summary_path": f"{dir_path}/{pmid}-summary.md"
            })

    return articles_to_process

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: REPORT_TYPE=MECFS python3 script.py <start_date_YYYY-MM-DD> [end_date_YYYY-MM-DD]")
        sys.exit(1)

    s_date = sys.argv[1]
    e_date = sys.argv[2] if len(sys.argv) > 2 else None

    found = scan_articles(s_date, e_date)
    print(f"Found {len(found)} articles to summarize across the specified date range.")
    # Agent/LLM uses this structured list to read, summarize, and map treatments
```

Run it with `REPORT_TYPE` set:
```bash
REPORT_TYPE=MECFS python process_articles.py 2026-05-25 2026-05-25
```

---

## Verification Checklist

- [ ] First checked if any article directories exist for the date range. If none found, skipped without writing anything.
- [ ] **Skipped memory/session_search calls** (disabled in cron) — used variables from the prompt directly.
- [ ] **Skipped already-summarized articles** — only read and processed new articles.
- [ ] **Batch-read** article data with `execute_code` where possible.
- [ ] **Used grep/search_files** to check existing treatment profiles instead of reading them all.
- [ ] **Skipped todo tool** — not useful in cron context.
- [ ] **Skipped post-write verification** — `write_file` return confirms success.
- [ ] Every new article in the specified date folders has a corresponding `{pmid}-summary.md` generated.
- [ ] Article summaries are written in clean, layperson-accessible prose devoid of unexplained medical jargon.
- [ ] Off-topic articles (tier 3) handled with minimal placeholder summaries — no time wasted on non-relevant content.
- [ ] Processing order: Tier 1 (directly relevant) before Tier 2 (marginal) before Tier 3 (not relevant).
- [ ] All treatments evaluated or heavily discussed in the processed literature are identified.
- [ ] For each identified treatment, the corresponding file in `workspace/treatment-{REPORT_TYPE}/` is updated (or created) with study links, local summary paths, and structured status updates.
- [ ] Raw source files (`{pmid}.md` and `{pmid}-full.txt`) remain unchanged.
