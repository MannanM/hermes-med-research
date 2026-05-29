# Research Post Publisher — Markdown Post Structure

The research pipeline (`research-roundup` + `research-processor` + `research-post-writer`) produces `.md` files in `/opt/data/profiles/med-research/workspace/blog/` with this exact structure.

## File Naming

```
/opt/data/profiles/med-research/workspace/blog/{REPORT_TYPE}-post-YYYY-MM-DD.md
```

Examples: `MECFS-post-2026-05-25.md`, `MCAS-post-2026-05-24.md`

## Structural Layout

```
Line | Content                    | Semantics
-----|----------------------------|--------------------------------
  1  | # TITLE: Subtitle          | H1: Post title. Text before `:` = title, after = Substack subtitle.
  2  |                            | (blank)
  3  | ### Subtitle paragraph     | H3: Editorial intro sentence. Goes in body, NOT Substack subtitle.
  4  |                            | (blank)
  5  | > **Date:** YYYY-MM-DD     | Blockquote: metadata -- SKIP
  6  | > **Covered Range:** ...   | Blockquote: metadata -- SKIP
  7  | > **Editor's Note:** ...   | Blockquote: metadata -- SKIP
  8  |                            | (blank)
  9  | ---                        | HR: BODY STARTS HERE
 10  |                            | (blank)
 11  | ## The Big Picture: ...    | H2: First body section heading
 12  |                            |
 13  | Body paragraphs...         | Body content begins
 14  |                            |
 15  | ---                        | Section separator
 16  |                            |
 17  | ## Deep Dive: ...          | Next section
...  | ...                        | ...
```

## Section Pattern

The post body (after the first `---`) typically contains these sections:

1. **The Big Picture** -- H2 section, introductory overview connecting the papers
2. **Deep Dive: The Latest Research** -- H2 section with H3/H4 sub-sections per paper:
   - Each paper subsection: H4 paper title -> `<ul>` with lead authors/journal/Source Artifacts
   - Then plain-language summary paragraphs
3. **Practical Takeaways for the Community** -- H2 with `<ul>` of bullet takeaways
4. **Concluding Thoughts** -- H2 closing reflection
5. **Sources and Further Reading** -- H2 with `<ol>` of numbered references linking to PMID URLs

## Inline Markdown Used

| Markdown | Renders As |
|----------|------------|
| `**bold**` | `<strong>bold</strong>` |
| `*italic*` | `<em>italic</em>` |
| `[text](url)` | `<a href="url">text</a>` |
| `---` (separate line) | `<hr>` |
| `> text` | `<blockquote><p>text</p></blockquote>` |
| `- item` | `<ul><li>item</li></ul>` |
| `1. item` | `<ol><li>item</li></ol>` |
| `&amp;` / `&mdash;` | Already HTML-encoded, pass through as-is |

## Important Conventions

- The H1 line always contains the colon-based title/subtitle split
- The H3 line after the title is an editorial intro -- it goes in the BODY
- Metadata blockquotes (Date, Covered Range, Editor's Note) are always present and should be excluded from the body
- PMID links are absolute: `https://pubmed.ncbi.nlm.nih.gov/<ID>/`
- Internal links use relative paths: `../articles-{REPORT_TYPE}/YYYY-MM-DD/<PMID>-summary.md` -- keep them as-is in the body
