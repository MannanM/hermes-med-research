---
name: research-roundup
description: "Ingest scientific articles from PubMed for a date range, saving metadata and full-text files to date-specific folders under `workspace/articles-{REPORT_TYPE}/` while tracking processed PMIDs globally."
version: 4.3.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [research, pubmed, ingestion, artifacts, generic]
    related_skills: [cross-source-research]
---

# Research Roundup — PubMed Article Ingest

Query PubMed for publications matching a `REPORT_TYPE`'s mapped search query within a date range, download metadata and full text, and partition them by publication date into `/opt/data/profiles/med-research/workspace/articles-{REPORT_TYPE}/`.

---

## Prerequisites

Define these variables before running the pipeline:

| Variable | Example | Purpose |
|---|---|---|
| `REPORT_TYPE` | `MECFS` | Mapped search query and output directory name |
| `REPORT_DATE_FROM` | `2026-05-25` | Start date (YYYY-MM-DD) |
| `REPORT_DATE_TO` | `2026-05-25` | End date (YYYY-MM-DD) |

### Cron Tip: Don't Hunt for Variables

**You're in a cron session.** Do NOT call `memory()`, `session_search()`, or read `.last_run` files to find input variables — they will fail silently or waste tool calls.

Instead, use the variables already provided to you in the cron job prompt or task context (`REPORT_TYPE`, `REPORT_DATE_FROM`, `REPORT_DATE_TO`). They are there — read them from your own instructions, not from external sources.

---

### Cron Optimization Rules

Apply these rules to all cron sessions to minimize tool call overhead:

1. **Skip todo tool** — Do NOT use `todo()` in cron context. Track progress in your own reasoning.
2. **Batch file reads** — When reading multiple article files (metadata or full-text), use `execute_code` with a Python loop and `from hermes_tools import read_file` to batch all reads into a single call. Never issue sequential `read_file()` for each article.
3. **Skip post-write verification** — Do NOT `ls` or `terminal` after writing files. `write_file` returns success confirmation.
4. **Compress turn sequences** — Plan reads, writes, and checks in larger batches. Avoid intermediary "let me now X" messages between tool calls.
5. **Skip already-done work** — Before QC-scanning, check if articles were already tagged with `[RELEVANT]`/`[FALSE POSITIVE]` in a previous run by examining the metadata files once.

---

## REPORT_TYPE → SEARCH_QUERY Mapping

If `REPORT_TYPE` is not in this table, make a reasonable guess for the search query, run the pipeline, and then use `skill_manage(action='patch')` to update this skill with the new mapping.

| REPORT_TYPE    | SEARCH_QUERY (PubMed)                                               | Notes |
|----------------|---------------------------------------------------------------------|---|
| `MECFS`        | `(ME/CFS OR myalgic encephalomyelitis OR chronic fatigue syndrome)` | |
| `MCAS`         | `(MCAS OR mast cell activation syndrome OR mastocytosis)`           | High false-positive rate. Run QC screening. |
| `LONG_COVID`   | `(post-COVID OR long COVID OR PASC OR post-acute sequelae)`         | |
| `POTS`         | `(POTS OR postural orthostatic tachycardia syndrome)`               | |
| `FIBROMYALGIA` | `(fibromyalgia OR fibrositis)`                                      | |
| `HYPER`        | `(hypermobility OR hypermobile OR joint instability)`               | |

---

## False Positive Mitigation

Acronyms (e.g., `MCAS`, `POTS`) or broad terms can generate false positives. Run a QC screen after ingestion to tag articles as `[RELEVANT]` or `[FALSE POSITIVE]` based on keywords in the title, abstract, or body.

### QC Screening Reference
- **MCAS**: `mast cell`, `mastocytosis`, `tryptase`, `KIT`, `anaphylaxis`, `urticaria`, `antihistamine`, `cromolyn`, `omalizumab`
- **POTS**: `postural orthostatic`, `tachycardia`, `dysautonomia`, `orthostatic intolerance`
- **MECFS**: `me/cfs`, `myalgic encephalomyelitis`, `chronic fatigue syndrome`, `postexertional malaise`, `pem`

> **⚠️ Pitfall — Substring matching in QC:** Short markers like `cfs`, `pem`, `mcas`, or `pots` will produce false positives via substring matching. For example, `cfs` matches inside `articles-MECFS` (a file path), and `pem` matches inside unrelated words containing `pem`. **Always use regex word boundaries** (`\\bcfs\\b`, `\\bpem\\b`) when checking these markers programmatically, and exclude the Artifact Metadata section of the `.md` file (which contains path strings with the REPORT_TYPE name) before searching.

### Running the QC Check

```python
import re

def is_relevant_article(pmid_dir: str, pmid: str, relevance_markers: list[str]) -> bool:
    \"\"\"Check article relevance using regex word-boundary matching.
    
    Uses regex boundaries (\\b) to avoid false positives from:
    - Short acronyms (cfs matches inside 'MECFS' paths)
    - Three-letter markers (pem matches inside unrelated words)
    Excludes the Artifact Metadata section which contains REPORT_TYPE path strings.
    \"\"\"
    md_path = f"{pmid_dir}/{pmid}.md"
    full_path = f"{pmid_dir}/{pmid}-full.txt"
    combined_text = ""

    for p in [md_path, full_path]:
        if os.path.exists(p):
            with open(p) as f:
                text = f.read()
                # Strip artifact metadata section (contains REPORT_TYPE in paths)
                if "## Artifact Metadata" in text:
                    text = text.split("## Artifact Metadata")[0]
                combined_text += text.lower() + " "

    # Build regex with word boundaries -- prevents substring false matches
    pattern = r'\b(' + '|'.join(re.escape(m) for m in relevance_markers) + r')\b'
    return bool(re.search(pattern, combined_text))
```

Then tag each article in the scan output: `[RELEVANT]` vs `[FALSE POSITIVE]`. This lets downstream skills (research-processor, research-post-writer) skip noise automatically.

---

## Output Architecture

Articles are saved into folders matching each article's actual publication date (`YYYY-MM-DD`). If a PMID has already been processed (exists in `/opt/data/profiles/med-research/workspace/processed.txt`), it is skipped to avoid redundant downloads and API calls.

```
workspace/
├── processed.txt                      # Centralized processed PMID log
└── articles-{REPORT_TYPE}/            # e.g., articles-MECFS, articles-MCAS
    └── 2026-05-25/
        ├── 38102345.md               # Metadata file
        └── 38102345-full.txt         # Full text or abstract fallback
```

---

## Step 1: Query PubMed (Search & ID Fetch)

Convert the hyphenated dates to PubMed slash format (`YYYY/MM/DD`). Always run and merge both `pdat` (publication date) and `edat` (entry date) queries to ensure no newly indexed articles are missed.

```bash
# Query pdat
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=${SEARCH_QUERY}&mindate=${START_DATE}&maxdate=${END_DATE}&datetype=pdat&retmax=100&retmode=json" > /tmp/pdat.json

# Query edat
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=${SEARCH_QUERY}&mindate=${START_DATE}&maxdate=${END_DATE}&datetype=edat&retmax=100&retmode=json" > /tmp/edat.json
```

Extract PMIDs from both files, deduplicate them, and fetch the combined XML payload.

---

## Step 2: Fetch XML Payload

```bash
# Replace P1,P2,P3 with comma-separated, deduplicated PMIDs
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=P1,P2,P3&retmode=xml&rettype=abstract" -o /tmp/pubmed_raw.xml
```

---

## Step 3: Parse and Partition (Python Script)

Save this script as `ingest_pubmed.py` and run it. It reads `/opt/data/profiles/med-research/workspace/processed.txt` to skip already-ingested articles, saving bandwidth and local storage.

```python
import os
import xml.etree.ElementTree as ET
import urllib.request
from datetime import datetime

REPORT_TYPE = os.environ.get("REPORT_TYPE", "UNKNOWN")
BASE_DIR = f"workspace/articles-{REPORT_TYPE}"
PROCESSED_FILE = "/opt/data/profiles/med-research/workspace/processed.txt"

def load_processed_pmids():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    return set()

def mark_pmid_processed(pmid):
    os.makedirs(os.path.dirname(PROCESSED_FILE), exist_ok=True)
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{pmid}\n")

def parse_date(article):
    # 1. ArticleDate
    art_date = article.find('.//ArticleDate')
    if art_date is not None:
        y, m, d = art_date.find('Year'), art_date.find('Month'), art_date.find('Day')
        if y is not None and m is not None and d is not None:
            return f"{y.text}-{m.text.zfill(2)}-{d.text.zfill(2)}"

    # 2. PubMedPubDate
    for pub_status in ['pubmed', 'entrez']:
        el = article.find(f'.//PubMedPubDate[@PubStatus="{pub_status}"]')
        if el is not None:
            y, m, d = el.find('Year'), el.find('Month'), el.find('Day')
            if y is not None and m is not None and d is not None:
                return f"{y.text}-{m.text.zfill(2)}-{d.text.zfill(2)}"

    # 3. JournalIssue PubDate fallback
    j_date = article.find('.//JournalIssue/PubDate')
    if j_date is not None:
        y = j_date.find('Year')
        if y is not None:
            m_map = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
                'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }
            m = j_date.find('Month')
            month = m_map.get(m.text.lower()[:3], '01') if m is not None and m.text else '01'
            d = j_date.find('Day')
            day = d.text.zfill(2) if d is not None and d.text else '01'
            return f"{y.text}-{month}-{day}"

    return datetime.now().strftime("%Y-%m-%d")

def ingest_articles(xml_path):
    processed_pmids = load_processed_pmids()
    tree = ET.parse(xml_path)
    root = tree.getroot()

    for article in root.findall('.//PubmedArticle'):
        medline = article.find('.//MedlineCitation')
        if medline is None:
            continue

        pmid = medline.find('PMID').text if medline.find('PMID') is not None else ''
        if not pmid:
            continue

        if pmid in processed_pmids:
            print(f"Skipping already processed PMID: {pmid}")
            continue

        art = medline.find('.//Article')
        if art is None:
            continue

        pub_date_str = parse_date(article)
        out_dir = f"{BASE_DIR}/{pub_date_str}"
        os.makedirs(out_dir, exist_ok=True)

        title_el = art.find('.//ArticleTitle')
        title = ''.join(title_el.itertext()).strip() if title_el is not None else 'Untitled'

        authors = []
        for author in art.findall('.//Author'):
            ln = author.find('LastName')
            fn = author.find('ForeName')
            if ln is not None:
                authors.append(f"{fn.text if fn is not None else ''} {ln.text}".strip())
        author_str = ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else "")

        journal = art.find('.//Journal/Title')
        journal_name = journal.text if journal is not None else ''
        doi_el = article.find('.//ArticleId[@IdType="doi"]')
        doi = doi_el.text if doi_el is not None else 'None'
        pmc_el = article.find('.//ArticleId[@IdType="pmc"]')
        pmc = pmc_el.text if pmc_el is not None else 'None'

        abstract_parts = art.findall('.//AbstractText')
        abstract = ' '.join([''.join(a.itertext()) for a in abstract_parts]).strip()

        kw_list = medline.find('.//KeywordList')
        keywords = ", ".join([kw.text for kw in kw_list.findall('Keyword') if kw.text]) if kw_list is not None else 'None'

        meta_content = f"""# {title}

> **PMID:** {pmid} | **DOI:** {doi} | **PMC:** {pmc}
> **Journal:** {journal_name} | **Published:** {pub_date_str}
> **Authors:** {author_str}

---

## Abstract

{abstract if abstract else "No abstract available."}

---

## Keywords
{keywords}

---

## Artifact Metadata
- **Retrieved:** {datetime.now().strftime("%Y-%m-%d")}
- **Local File Path:** {BASE_DIR}/{pub_date_str}/{pmid}.md
- **Full Text Path:** {BASE_DIR}/{pub_date_str}/{pmid}-full.txt
"""
        with open(f"{out_dir}/{pmid}.md", "w", encoding="utf-8") as f:
            f.write(meta_content)

        full_text_path = f"{out_dir}/{pmid}-full.txt"
        full_text_saved = False

        if pmc != 'None':
            try:
                pmc_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pmc}&retmode=xml"
                with urllib.request.urlopen(pmc_url, timeout=10) as response:
                    pmc_xml = response.read()
                pmc_tree = ET.ElementTree(ET.fromstring(pmc_xml))
                paragraphs = pmc_tree.findall('.//body//p')
                full_text_body = "\n\n".join([''.join(p.itertext()).strip() for p in paragraphs if p.itertext()])

                if full_text_body.strip():
                    with open(full_text_path, "w", encoding="utf-8") as f:
                        f.write(f"--- PMC Full Text ({pmc}) ---\n\n" + full_text_body)
                    full_text_saved = True
            except Exception:
                pass

        if not full_text_saved:
            with open(full_text_path, "w", encoding="utf-8") as f:
                f.write(f"--- Abstract Fallback ---\n\n{abstract}")

        mark_pmid_processed(pmid)

if __name__ == "__main__":
    import sys
    xml_file = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pubmed_raw.xml"
    ingest_articles(xml_file)
```

Run with the environment variable set:
```bash
REPORT_TYPE=MECFS python ingest_pubmed.py
```

---

## Verification Checklist

- [ ] Mapped `REPORT_TYPE` to retrieve `SEARCH_QUERY`.
- [ ] Read variables from context/cron prompt — no memory/session_search/.last_run.
- [ ] Merged results from both `pdat` and `edat` queries.
- [ ] Verified that the script correctly loads `/opt/data/profiles/med-research/workspace/processed.txt` and skips existing PMIDs.
- [ ] Saved files inside `workspace/articles-{REPORT_TYPE}/{actual_pub_date}/`.
- [ ] Appended processed PMIDs to `/opt/data/profiles/med-research/workspace/processed.txt` upon successful execution.
- [ ] **Cron only:** Did NOT use `todo()`, did NOT read files sequentially, did NOT verify writes, did NOT use memory/session_search.
