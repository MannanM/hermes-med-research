#!/usr/bin/env python3
"""
Convert research blog post markdown body to HTML for Substack editor injection.

Usage: python3 convert_md_to_html.py [--input-markdown <multiline string or stdin>]

Takes the body markdown (everything after the first --- HR in the blog post file)
and returns clean HTML suitable for setting innerHTML on the Substack contenteditable div.

Conversion rules:
  - ## H2 -> <h2>
  - ### H3 -> <h3>
  - #### H4 -> <h4>
  - Inline **bold** -> <strong>
  - Inline *italic* -> <em> (single asterisk) or <em> (underscore)
  - [text](url) -> <a href="url">text</a>
  - ![alt](src) -> <img src="src" alt="alt">
  - --- on its own line -> <hr>
  - > text (blockquote) -> <blockquote><p>text</p></blockquote>
  - - item (unordered list) -> <ul><li>item</li></ul>
  - 1. item (ordered list) -> <ol><li>item</li></ol>
  - Blank-line-separated text -> <p> wrappers
  - HTML entities (&amp;, &mdash;, &ldquo;) pass through as-is
"""

import re
import sys


def convert(markdown: str) -> str:
    """Convert post-body markdown to HTML for Substack."""
    lines = markdown.splitlines()
    html_parts = []
    in_ul = False
    in_ol = False
    in_blockquote = False

    def close_ul():
        nonlocal in_ul
        if in_ul:
            html_parts.append("</ul>")
            in_ul = False

    def close_ol():
        nonlocal in_ol
        if in_ol:
            html_parts.append("</ol>")
            in_ol = False

    def close_blockquote():
        nonlocal in_blockquote
        if in_blockquote:
            html_parts.append("</blockquote>")
            in_blockquote = False

    def inline(line: str) -> str:
        """Process inline elements."""
        # Images first
        line = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', line)
        # Links
        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', line)
        # Bold
        line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
        # Italic
        line = re.sub(r"\*(.+?)\*", r"<em>\1</em>", line)
        line = re.sub(r"_(.+?)_", r"<em>\1</em>", line)
        return line

    for raw_line in lines:
        stripped = raw_line.strip()

        # Horizontal rule
        if stripped == "---":
            close_ul()
            close_ol()
            close_blockquote()
            html_parts.append("<hr>")
            continue

        # Blank line — close open tags
        if not stripped:
            close_ul()
            close_ol()
            close_blockquote()
            continue

        # Blockquote
        if stripped.startswith("> "):
            close_ul()
            close_ol()
            content = inline(stripped[2:])
            if not in_blockquote:
                html_parts.append("<blockquote>")
                in_blockquote = True
            html_parts.append(f"<p>{content}</p>")
            continue

        close_blockquote()

        # Headings
        h_match = re.match(r"^(#{2,4})\s+(.+)$", stripped)
        if h_match:
            close_ul()
            close_ol()
            level = len(h_match.group(1))
            content = inline(h_match.group(2))
            html_parts.append(f"<h{level}>{content}</h{level}>")
            continue

        # Unordered list item
        if stripped.startswith("- "):
            close_ol()
            close_blockquote()
            content = inline(stripped[2:])
            if not in_ul:
                html_parts.append("<ul>")
                in_ul = True
            html_parts.append(f"<li>{content}</li>")
            continue

        close_ul()

        # Ordered list item
        ol_match = re.match(r"^\d+\.\s+(.+)$", stripped)
        if ol_match:
            close_ul()
            close_blockquote()
            content = inline(ol_match.group(1))
            if not in_ol:
                html_parts.append("<ol>")
                in_ol = True
            html_parts.append(f"<li>{content}</li>")
            continue

        close_ol()

        # Default: paragraph
        content = inline(stripped)
        html_parts.append(f"<p>{content}</p>")

    # Close any remaining open tags
    close_ul()
    close_ol()
    close_blockquote()

    return "\n".join(html_parts)


def main():
    markdown = None
    if len(sys.argv) > 2 and sys.argv[1] == "--input-markdown":
        markdown = sys.argv[2]
    elif not sys.stdin.isatty():
        markdown = sys.stdin.read()

    if not markdown:
        print("ERROR: No markdown input provided. Pass via --input-markdown or pipe to stdin.", file=sys.stderr)
        sys.exit(1)

    html = convert(markdown)
    print(html)


if __name__ == "__main__":
    main()
