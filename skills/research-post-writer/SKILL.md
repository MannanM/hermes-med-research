---
name: research-post-writer
description: "Aggregate patient-facing research summaries over a date range, identify overarching biological themes, and write an editorial science newsletter (Substack style) saved to workspace/blog/."
version: 4.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [writing, science-communication, blogging, research-translation]
    related_skills: [research-roundup, research-processor]
---

# Research Post Writer

Synthesize multiple plain-language research summaries across a target date range into a cohesive, narrative-driven and highly readable newsletter draft for a college-educated patient and scientific community (such as a Substack publication).

Rather than listing studies chronologically, this skill helps identify structural or biological connections between independent papers and frames them within the broader landscape of clinical research.

---

## Prerequisites -- Set These Before Starting

| Variable | Example | Purpose |
|---|---|---|
| `REPORT_TYPE` | `MECFS` | Controls which article directory to scan and the output filename |
| `REPORT_DATE_FROM` | `2026-05-25` | Start of date range (YYYY-MM-DD) |
| `REPORT_DATE_TO` | `2026-05-25` | End of date range (YYYY-MM-DD) |

---

## When to Use

- To draft a weekly, bi-weekly, or monthly digest of research updates
- When requested to "write a blog post" or "draft a newsletter update" for a specific date range of findings

---

## ⚙️ Cron Context: Rules for Automated Runs

When this skill runs non-interactively (as a cron job), the following rules apply to avoid wasted tool calls in an unsupervised environment. **You MUST follow them — every wasted call adds latency and token cost.**

### 1. Don't Hunt for Variables

**Do NOT call `memory()`, `session_search()`, or try to read `.last_run` files to find input variables** — these either fail or waste tool calls in cron context.

Your input variables (`REPORT_TYPE`, `REPORT_DATE_FROM`, `REPORT_DATE_TO`) are provided in your task context or prompt — **use them directly, don't go hunting.**

### 2. Batch Read Files

**Do NOT read metadata and summary files in separate sequential calls.** One `read_file()` per file wastes a tool call turn each. Instead, load the linked `scripts/collect_summaries.py` script via `skill_view(file_path='scripts/collect_summaries.py')` and run it via `execute_code` in a single call to gather all article content at once.

### 3. Skip Todo in Cron

**Do NOT use the `todo` tool in cron context** — there is no human reading your progress updates. Track progress in your own reasoning.

### 4. Skip Post-Write Verification

**Do NOT read back or `ls` files after writing them** — `write_file` returns `bytes_written` and `dirs_created`, which confirms success. Post-write reads are wasted tool calls.

### 5. Compress Turn Sequences

Plan and execute in bulk. **Read all summaries, compute the editorial angle, then write the post — all in the minimum number of turns.** Avoid intermediary "let me now X" messages between steps.

---

## No-Op Guard: Check If Any Summaries Exist

Before writing, check whether any `*-summary.md` files exist in `/opt/data/profiles/med-research/workspace/articles-{REPORT_TYPE}/` for the date range. Use the linked `scripts/collect_summaries.py` (or a quick `search_files`) — if the collection is empty, skip; do not create an empty blog post file.

---

## Output Architecture

The final blog posts are stored in the blog directory, named using `REPORT_TYPE` and the end date of the range:

```text
/opt/data/profiles/med-research/workspace/
├── articles-{REPORT_TYPE}/
│   └── YYYY-MM-DD/
│       └── PMID12345-summary.md
└── blog/
    └── {REPORT_TYPE}-post-YYYY-MM-DD.md    # Synthesized newsletter draft
```

---

## Step 1: Gather and Analyze Summaries

Iterate through the specified date range and extract all `*-summary.md` files from `/opt/data/profiles/med-research/workspace/articles-{REPORT_TYPE}/{date}/`.

Before writing, analyze the collection to identify **biological intersections** or **common threads**. Examples of connecting threads include:

- **Immunological dysfunction** (NK cell activity, autoantibodies, T-cell exhaustion)
- **Mitochondrial/Metabolic strain** (ATP production, glycolysis, metabolomics)
- **Neurological/Autonomic pathways** (neuroinflammation, microglial activation, small fiber neuropathy, orthostatic intolerance)
- **Vascular/Perfusion issues** (endothelial dysfunction, microclots, oxygen extraction)

---

## Step 2: Shape the Editorial Structure

A good science newsletter reads like a conversation, not a report card. The structure should feel natural:

- **Title and subtitle**: Informative and clear without resorting to clickbait or exaggerated claims of "cures."
- **Editorial hook (the connecting thread)**: An opening essay of 2-3 paragraphs introducing the week's biological theme and explaining how the latest papers contribute to this puzzle piece.
- **Themed deep dives**: Breakdowns of the studies grouped under thematic headings, not isolated paper reviews.
- **Clinical and patient takeaways**: What these findings mean practically for patients, clinicians, and ongoing clinical trials.
- **Looking ahead**: A brief concluding thought on the trajectory of this line of research.
- **Detailed references**: Footnoted or styled academic references linking back to official PMIDs, DOIs, and the local summary artifacts.

The tone should be warm and curious, like a knowledgeable friend explaining recent discoveries. Avoid robotic structure like numbered lists or labeled sections ("Topic 1", "Topic 2"). Instead, let the science guide the flow -- start with the most compelling finding or the broadest theme and build from there.

---

## Step 3: Substack Post Template (`/opt/data/profiles/med-research/workspace/blog/{REPORT_TYPE}-post-YYYY-MM-DD.md`)

Generate the draft using the following markdown structure. Note the human-sounding style: no numbered topics, no em dashes (use regular dashes or commas instead):

```markdown
# {{Title: e.g., Unraveling the Energy Grid: New Insights into Mitochondria and Neuroinflammation}}

### {{Subtitle paragraph -- goes in body, NOT Substack subtitle field}}

> **Date:** YYYY-MM-DD
> **Covered Range:** {{Start Date}} to {{End Date}}
> **Editor's Note:** This post translation is for educational and informational purposes only. It does not constitute medical advice.

---

## The Big Picture: {{Connecting Theme Name}}

A 3-paragraph editorial synthesis. Detail how the studies processed during this period intersect. For example, if one study looks at vascular flow and another at mitochondrial output, explain how restricted blood flow directly starves cellular powerhouses, linking the papers together.

---

## Deep Dive: The Latest Research

### {{Natural Biological Theme Heading, e.g., Cellular Energy Deficits under the Microscope}}

Introduce the focus. Integrate the findings of the relevant studies here.

#### {{Study Title 1 (use the actual study title, not "Topic 1")}}
- **Lead Authors:** {{Authors}} | **Journal:** {{Journal Name}}
- **Source Artifacts:** [PMID {{pmid}}](https://pubmed.ncbi.nlm.nih.gov/{{pmid}}/) | [Plain Language Summary](../articles-{REPORT_TYPE}/{{date}}/{{pmid}}-summary.md)

Detailed narrative breakdown of the study (3-4 paragraphs). Focus on explaining *how* the researchers reached their conclusions, what methods they used (e.g., in vitro muscle cells, symptom surveys), and the direct implications. Use clear analogies for complex mechanics.

---

#### {{Next Study Title}}
- **Lead Authors:** {{Authors}} | **Journal:** {{Journal Name}}
- **Source Artifacts:** [PMID {{pmid}}](https://pubmed.ncbi.nlm.nih.gov/{{pmid}}/) | [Plain Language Summary](../articles-{REPORT_TYPE}/{{date}}/{{pmid}}-summary.md)

Detailed narrative breakdown of the next study or cluster of studies.

---

## Practical Takeaways for the Community

What does this collective research mean for patients in their daily lives or discussions with their doctors?

- **Diagnostic Progress:** (e.g., "While not yet a clinical test, the tracking of NK cell markers brings researchers closer to validating biomarkers.")
- **Treatment Implications:** (e.g., "The study on [Treatment] suggests that supporting mitochondrial output might require addressing vascular perfusion first.")
- **Trial Watch:** (e.g., "These mechanisms support the ongoing phase II trial of [Drug].")

---

## Concluding Thoughts

A short sign-off wrapping up the progress. Keep expectations grounded - acknowledge the slow, incremental nature of research while validating the importance of each new piece of data.

---

## Sources and Further Reading

1. {{Author Lastname, First Initial}}. (Year). *{{Paper Title}}*. {{Journal Name}}. [PMID: {{pmid}}](https://pubmed.ncbi.nlm.nih.gov/{{pmid}}/)
2. {{Author Lastname, First Initial}}. (Year). *{{Paper Title}}*. {{Journal Name}}. [PMID: {{pmid}}](https://pubmed.ncbi.nlm.nih.gov/{{pmid}}/)
```

---

## Step 4: Collect Input Summaries (Batch Read)

**Do NOT read files one-by-one with individual `read_file` calls.** Use the linked script instead:

1. Load the script: `skill_view(name='research-post-writer', file_path='scripts/collect_summaries.py')`
2. Run it via `execute_code` — it reads all `*-summary.md` files from `/opt/data/profiles/med-research/workspace/articles-{REPORT_TYPE}/{date}/` for the date range in a single call and prints their full content to stdout.

If the script outputs "Collected 0 summaries", skip — do not create a blog post.

---

## Verification Checklist

- [ ] **Cron rules**: Used variables from context/prompt directly; did NOT call `memory()`, `session_search()`, or read config files
- [ ] **Batch reads**: Used `skill_view(file_path='scripts/collect_summaries.py')` then ran via `execute_code` — did NOT read files sequentially one per tool call
- [ ] **No todo overhead**: Skipped `todo` tool entirely (cron context: no human reading progress)
- [ ] **No post-write verification**: Did NOT read back or `ls` files after writing
- [ ] **Efficient turns**: All content gathered in minimal turns before writing
- [ ] First checked whether any `*-summary.md` files exist for the date range. If none found, skipped without creating a post file.
- [ ] The output file is written to `/opt/data/profiles/med-research/workspace/blog/{REPORT_TYPE}-post-YYYY-MM-DD.md`.
- [ ] The blog post is not a simple bulleted list; it has a clear editorial theme that connects the research conceptually.
- [ ] The writing sounds human: no numbered topic labels, no em dashes.
- [ ] Complex concepts are written in an engaging, narrative style suitable for a platform like Substack.
- [ ] Every study cited has its PMID link and local summary artifact referenced properly.
- [ ] The tone is warm, curious and constructive - avoiding premature declarations of cures or sensationalizing scientific steps.
