#!/usr/bin/env python3
"""Convert ME/CFS markdown research report to styled HTML and send via AgentMail."""

import re
import json
import os

# ── Read source ──────────────────────────────────────────────────────────────
md_path = "/opt/data/workspace/research-2026-05-24.md"
with open(md_path, "r") as f:
    md = f.read()

# ── Preserve code blocks first ──────────────────────────────────────────────
code_blocks = []
def _save_code(m):
    code_blocks.append(m.group(0))
    return f"%%CODE_{len(code_blocks)-1}%%"
md = re.sub(r'```[\s\S]*?```', _save_code, md)
md = re.sub(r'(?<!\n)`[^`]+`', _save_code, md)

# ── Convert markdown elements ────────────────────────────────────────────────

# Horizontal rules
md = re.sub(r'^---+$', '<hr>', md, flags=re.MULTILINE)

# Headings
md = re.sub(r'^#### ([^#].*)$', r'<h4>\1</h4>', md, flags=re.MULTILINE)
md = re.sub(r'^### ([^#].*)$', r'<h3>\1</h3>', md, flags=re.MULTILINE)
md = re.sub(r'^## ([^#].*)$', r'<h2>\1</h2>', md, flags=re.MULTILINE)
md = re.sub(r'^# ([^#].*)$', r'<h1>\1</h1>', md, flags=re.MULTILINE)

# Bold + italic simultaneously ***...***
md = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', md)
# Bold **...**
md = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', md)
# Italic *...* (but not markdown table pipes or multiplication)
md = re.sub(r'(?<!\*)\*(?!\*)([^*\n]+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', md)

# Strikethrough
md = re.sub(r'~~(.+?)~~', r'<del>\1</del>', md)

# Inline code (backticks, single)
md = re.sub(r'`([^`]+)`', r'<code>\1</code>', md)

# Links [text](url)
md = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', md)

# Images ![alt](url)
md = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img src="\2" alt="\1">', md)

# Blockquotes (> lines)
lines = md.split('\n')
in_blockquote = False
new_lines = []
for line in lines:
    if re.match(r'^>\s?(.*)', line):
        content = re.sub(r'^>\s?(.*)', r'\1', line)
        if not in_blockquote:
            new_lines.append('<blockquote>')
            in_blockquote = True
        new_lines.append(content)
    else:
        if in_blockquote:
            new_lines.append('</blockquote>')
            in_blockquote = False
        new_lines.append(line)
if in_blockquote:
    new_lines.append('</blockquote>')
md = '\n'.join(new_lines)

# Unordered lists
lines = md.split('\n')
in_ul = False
out = []
for line in lines:
    stripped = line.lstrip()
    if stripped.startswith('- ') or stripped.startswith('* '):
        indent_level = len(line) - len(stripped)
        content = stripped[2:]
        if not in_ul:
            out.append('<ul>')
            in_ul = True
        out.append(f'<li>{content}</li>')
    else:
        if in_ul:
            out.append('</ul>')
            in_ul = False
        out.append(line)
if in_ul:
    out.append('</ul>')
md = '\n'.join(out)

# Tables (simple pipe tables)
def _convert_table(m):
    rows = m.group(0).strip().split('\n')
    header_cols = [c.strip() for c in rows[0].split('|') if c.strip()]
    # Skip separator row (|---|)
    html = '<table>\n<thead>\n<tr>'
    for col in header_cols:
        html += f'<th>{col}</th>'
    html += '</tr>\n</thead>\n<tbody>\n'
    for row in rows[2:]:
        cols = [c.strip() for c in row.split('|') if c.strip()]
        if cols:
            html += '<tr>'
            for col in cols:
                html += f'<td>{col}</td>'
            html += '</tr>\n'
    html += '</tbody>\n</table>'
    return html

md = re.sub(r'\|[^\n]+\|\n\|[-| ]+\|\n(\|[^\n]+\|\n?)+', _convert_table, md, flags=re.MULTILINE)

# Restore code blocks
for i, block in enumerate(code_blocks):
    # Check if it's a fenced code block
    if block.startswith('```'):
        # Extract language if present
        lang_match = re.match(r'```(\w*)', block)
        lang = lang_match.group(1) if lang_match else ''
        code_content = re.sub(r'```\w*\n', '', block)
        code_content = re.sub(r'\n```$', '', code_content)
        # Escape HTML in code
        code_content = code_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        html_class = f' class="language-{lang}"' if lang else ''
        replacement = f'<pre><code{html_class}>{code_content}</code></pre>'
    else:
        # Inline code
        content = block.strip('`')
        content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        replacement = f'<code>{content}</code>'
    md = md.replace(f'%%CODE_{i}%%', replacement)

# Handle remaining markdown tables (without leading pipe)
# Fix any double blank lines
md = re.sub(r'\n{3,}', '\n\n', md)

# Wrap paragraphs (text between block-level elements)
lines = md.split('\n')
in_p = False
out = []
for line in lines:
    stripped = line.strip()
    is_block = (stripped.startswith('<h') or stripped.startswith('</h') or
                stripped.startswith('<ul') or stripped.startswith('</ul') or
                stripped.startswith('<li') or stripped.startswith('</li') or
                stripped.startswith('<ol') or stripped.startswith('</ol') or
                stripped.startswith('<pre') or stripped.startswith('</pre') or
                stripped.startswith('<blockquote') or stripped.startswith('</blockquote') or
                stripped.startswith('<table') or stripped.startswith('</table') or
                stripped.startswith('<th') or stripped.startswith('</th') or
                stripped.startswith('<td') or stripped.startswith('</td') or
                stripped.startswith('<tr') or stripped.startswith('</tr') or
                stripped.startswith('<thead') or stripped.startswith('</thead') or
                stripped.startswith('<tbody') or stripped.startswith('</tbody') or
                stripped.startswith('<hr') or stripped == '')
    
    if is_block:
        if in_p:
            out.append('</p>')
            in_p = False
        out.append(line)
    else:
        if not in_p:
            out.append('<p>')
            in_p = True
        out.append(line)

if in_p:
    out.append('</p>')

md = '\n'.join(out)

# Clean up empty paragraphs
md = re.sub(r'<p>\s*</p>', '', md)

# ── Build full HTML document ─────────────────────────────────────────────────

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ME/CFS Research Roundup — May 17–24, 2026</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
    font-size: 16px;
    line-height: 1.7;
    color: #1a1a2e;
    background: #f7f8fa;
    padding: 0;
    margin: 0;
  }}

  .container {{
    max-width: 820px;
    margin: 0 auto;
    padding: 40px 24px;
  }}

  .header {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    color: #e8e8f0;
    padding: 48px 24px;
    text-align: center;
  }}

  .header h1 {{
    font-size: 1.8rem;
    font-weight: 700;
    margin: 0 0 8px;
    color: #fff;
  }}

  .header p {{
    font-size: 0.95rem;
    color: #a8a8c0;
    margin: 4px 0;
  }}

  .content {{
    background: #ffffff;
    border-radius: 12px;
    padding: 36px 32px;
    margin-top: 24px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  }}

  .content h1 {{
    font-size: 1.6rem;
    color: #1a1a2e;
    border-bottom: 2px solid #e8e8f0;
    padding-bottom: 10px;
    margin: 32px 0 16px;
  }}

  .content h1:first-child {{ margin-top: 0; }}

  .content h2 {{
    font-size: 1.3rem;
    color: #162447;
    margin: 28px 0 12px;
    padding-left: 0;
  }}

  .content h3 {{
    font-size: 1.1rem;
    color: #1b3a6b;
    margin: 22px 0 10px;
  }}

  .content h4 {{
    font-size: 1.05rem;
    color: #1f4287;
    margin: 18px 0 8px;
  }}

  .content p {{
    margin: 0 0 14px;
    color: #2d2d44;
  }}

  .content a {{
    color: #2563eb;
    text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: border-color 0.15s;
  }}

  .content a:hover {{
    border-bottom-color: #2563eb;
  }}

  .content hr {{
    border: none;
    border-top: 1px solid #e2e4eb;
    margin: 28px 0;
  }}

  .content blockquote {{
    background: #f4f6fa;
    border-left: 4px solid #2563eb;
    padding: 14px 18px;
    margin: 16px 0;
    border-radius: 0 6px 6px 0;
    color: #3a3a50;
    font-style: normal;
  }}

  .content blockquote p {{ margin: 0; }}

  .content ul, .content ol {{
    margin: 8px 0 14px;
    padding-left: 24px;
  }}

  .content li {{
    margin-bottom: 5px;
    color: #2d2d44;
  }}

  .content code {{
    font-family: "SF Mono", "Fira Code", "Fira Mono", Menlo, Consolas, monospace;
    background: #eef0f5;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
    color: #b91c1c;
  }}

  .content pre {{
    background: #1e1e2e;
    color: #cdd6f4;
    padding: 16px 20px;
    border-radius: 8px;
    overflow-x: auto;
    font-size: 0.85rem;
    line-height: 1.5;
    margin: 16px 0;
  }}

  .content pre code {{
    background: none;
    color: inherit;
    padding: 0;
    font-size: inherit;
    border-radius: 0;
  }}

  .content table {{
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 0.9rem;
  }}

  .content th {{
    background: #f0f2f7;
    text-align: left;
    padding: 10px 12px;
    font-weight: 600;
    color: #1a1a2e;
    border-bottom: 2px solid #d0d4e0;
  }}

  .content td {{
    padding: 9px 12px;
    border-bottom: 1px solid #e2e4eb;
    color: #2d2d44;
  }}

  .content tr:last-child td {{
    border-bottom: none;
  }}

  .footer {{
    text-align: center;
    color: #8888a0;
    font-size: 0.85rem;
    padding: 32px 24px;
  }}

  .footer a {{ color: #2563eb; text-decoration: none; }}

  .tag {{
    display: inline-block;
    background: #e8f0fe;
    color: #2563eb;
    font-size: 0.78rem;
    padding: 2px 10px;
    border-radius: 12px;
    margin: 2px 3px;
  }}

  .score {{ display: inline-block; background: #fef3c7; color: #92400e; font-size: 0.8rem; padding: 1px 8px; border-radius: 4px; }}

  @media (max-width: 600px) {{
    .content {{ padding: 20px 16px; }}
    .header h1 {{ font-size: 1.4rem; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>🩺 ME/CFS Research Roundup</h1>
  <p>May 17 – 24, 2026</p>
  <p style="font-size:0.85rem;color:#8888b0;">Sources: PubMed &middot; Reddit r/CFS</p>
</div>

<div class="container">
<div class="content">
{md}
</div>

<div class="footer">
  <p>Compiled on 2026-05-24 by <a href="#">Hermes Agent</a></p>
  <p style="margin-top:4px;">Data from PubMed NCBI E-utilities API &amp; Reddit JSON API</p>
</div>
</div>

</body>
</html>'''

# ── Write output ──────────────────────────────────────────────────────────────
output_path = "/opt/data/workspace/index.html"
with open(output_path, "w") as f:
    f.write(html)

print(f"✅ Written: {output_path} ({os.path.getsize(output_path)} bytes)")
print("✅ HTML conversion complete.")
