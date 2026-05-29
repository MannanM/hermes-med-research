---
name: research-post-publish
description: "Convert a compiled research blog post to HTML for manual copying to a publishing platform. Uses REPORT_TYPE to locate the post file and scripts/convert_md_to_html.py to render the body."
version: 4.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [research, html, conversion, blog, publishing]
    related_skills: [research-post-writer, research-processor, research-roundup]
---

# Research Post Publisher — HTML Export

Converts a compiled research blog post markdown file into clean HTML suitable for copying into any publishing platform's editor. The post filename is determined by `REPORT_TYPE` and the date from `REPORT_{REPORT_TYPE}_DATE_TO`.

---

## Prerequisites — Set These Before Starting

| Variable | Example | Purpose |
|---|---|---|
| `REPORT_TYPE` | `MECFS` | Used to construct the date variable name and the blog file path |
| `REPORT_{TYPE}_DATE_TO` | `REPORT_MECFS_DATE_TO=2026-05-25` | The date of the blog post; variable name is dynamic: `REPORT_{REPORT_TYPE}_DATE_TO` |

The LLM must construct the date variable name dynamically:
```bash
# For REPORT_TYPE=MECFS:
DATE_VAR="REPORT_MECFS_DATE_TO"
TARGET_DATE="${!DATE_VAR}"  # indirect expansion in bash
POST_FILE="workspace/blog/${REPORT_TYPE}-post-${TARGET_DATE}.md"
HTML_FILE="workspace/blog/${REPORT_TYPE}-post-${TARGET_DATE}.html"
```

**If `POST_FILE` does not exist, report "[SKIP]" and do nothing.**

---

## Efficiency: Automated Context

In cron contexts, follow these rules to minimize tool calls:

- **Don't hunt for variables**: REPORT_TYPE, REPORT_{TYPE}_DATE_TO are provided in your task context — use them directly. No memory(), session_search(), or file scans.
- **Skip todo**: Do not use the todo tool — track progress in your own reasoning.
- **Skip post-write verification**: Do not verify written files — trust tool return values.

---

## When to Use

- After `research-post-writer` has generated a post file
- When asked to "generate HTML for the post" or "export as HTML"
- As the final step of the research pipeline before manual publishing

---

## Step-by-Step: Convert to HTML

### 1. Locate and read the blog post file

Construct the file path and verify it exists:

```bash
REPORT_TYPE=MECFS
TARGET_DATE=2026-05-25
POST_FILE="workspace/blog/${REPORT_TYPE}-post-${TARGET_DATE}.md"
HTML_FILE="workspace/blog/${REPORT_TYPE}-post-${TARGET_DATE}.html"

if [ ! -f "$POST_FILE" ]; then
    echo "[SKIP] No post file found at ${POST_FILE} — nothing to convert."
    exit 0
fi
```

If the file exists, read its contents.

### 2. Extract title, subtitle, and body from markdown structure

The markdown file follows this structure (see `references/markdown-post-structure.md`):

```
# TITLE: Subtitle (optional)             <- H1 = post title, text before colon is title
                                          (blank line)
### Subtitle paragraph (editorial intro) <- H3 = editorial lead paragraph
                                          (blank line)
> **Date:** YYYY-MM-DD                    <- metadata blockquote (excluded)
> **Covered Range:** YYYY-MM-DD to YYYY-MM-DD
> **Editor's Note:** ...
                                          (blank line)
---                                       <- HR — BODY STARTS HERE
                                          (blank line)
## First section heading                  <- H2 = first body section
...
```

- **Title**: The first H1 line (`# TITLE: Subtitle`), text before `:`. Example:
  `# The Immune Crossroads: How a Calcium Channel Defect May Connect Post-Viral Syndromes`
  -> Title: `"The Immune Crossroads"`
  If the H1 has no colon, use the entire H1 text as the title.
- **Subtitle**: The text AFTER the colon in the H1 title line. Example above -> Subtitle: `"How a Calcium Channel Defect May Connect Post-Viral Syndromes"`. If the title has no colon, leave subtitle empty.
- **Body**: Everything from the first `---` (HR) onward. This excludes the title and the editorial metadata blockquotes.

### 3. Convert markdown to HTML for the body

Load the converter script:
`skill_view(name='research-post-publish', file_path='scripts/convert_md_to_html.py')`

Extract the body markdown (everything from the first `---` onward) and pipe it through the script via `execute_code`:

```python
from hermes_tools import terminal
result = terminal("python3 <script_path> < <body_tempfile>")
html = result["output"]
```

The script handles: headings (`<h2>`-`<h4>`), bold/italic, links, images, blockquotes, lists, `<hr>`, and HTML entity passthrough.

### 4. Assemble the complete HTML document

Wrap the converted body in a full HTML document with the title and metadata:

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{Title}}</title>
<meta name="description" content="{{Subtitle}}">
</head>
<body>
<h1>{{Title}}</h1>
<p><em>{{Subtitle}}</em></p>
<hr>
{{Converted Body HTML}}
</body>
</html>
```

### 5. Save the HTML file

Write the complete HTML document to `workspace/blog/${REPORT_TYPE}-post-${TARGET_DATE}.html`, alongside the markdown source.

---

## Subtitle Rules

The subtitle is the text after the colon in the H1 title, or empty if there's no colon. It goes in the `<meta description>` and as an `<em>` line below the `<h1>` in the HTML output. It is NOT the first body paragraph.

---

## Pitfalls

- **Post file doesn't exist**: Return "[SKIP]" silently — this is expected when there's nothing to convert yet.
- **Large body HTML**: The converted HTML can be several KB. `write_file` handles this without issues.

---

## Verification Checklist

- [ ] Dynamic date variable `REPORT_{REPORT_TYPE}_DATE_TO` constructed and resolved correctly (no hunting via memory/session_search).
- [ ] Blog file checked. Missing = "[SKIP]".
- [ ] Title and subtitle extracted from H1 colon split.
- [ ] Body starts at first `---`, excludes metadata blockquotes.
- [ ] Markdown converted to HTML via linked script (`scripts/convert_md_to_html.py`).
- [ ] Complete HTML document assembled and saved alongside the markdown file.
- [ ] Efficiency rules followed: no todo, no post-write verification, no hunting for variables.
