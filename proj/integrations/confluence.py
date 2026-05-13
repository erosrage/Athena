from __future__ import annotations
import re

from atlassian import Confluence
from rich.console import Console

console = Console()


def connect(base_url: str, token: str) -> Confluence:
    return Confluence(url=base_url, token=token)


def create_page(
    client: Confluence,
    space_key: str,
    title: str,
    body_md: str,
    parent_id: str | None = None,
) -> str:
    """Create a new page and return its ID."""
    result = client.create_page(
        space=space_key,
        title=title,
        body=_md_to_storage(body_md),
        parent_id=parent_id,
        representation="storage",
    )
    return str(result["id"])


def update_page(client: Confluence, page_id: str, title: str, body_md: str) -> None:
    """Replace a page's content with new Markdown."""
    client.update_page(
        page_id=page_id,
        title=title,
        body=_md_to_storage(body_md),
        representation="storage",
    )


def append_to_page(client: Confluence, page_id: str, title: str, section_md: str) -> None:
    """Prepend a new section to the top of an existing page (newest first)."""
    page = client.get_page_by_id(page_id, expand="body.storage")
    existing = page["body"]["storage"]["value"]
    new_body = _md_to_storage(section_md) + "\n<hr/>\n" + existing
    client.update_page(
        page_id=page_id,
        title=title,
        body=new_body,
        representation="storage",
    )


def get_page_url(base_url: str, page_id: str) -> str:
    return f"{base_url.rstrip('/')}/pages/viewpage.action?pageId={page_id}"


# ---------------------------------------------------------------------------
# Markdown → Confluence storage format (XHTML subset)
# ---------------------------------------------------------------------------

def _md_to_storage(md: str) -> str:
    # Fenced code blocks — process before any other substitution
    def _code_block(m: re.Match) -> str:
        lang = m.group(1) or "none"
        code = m.group(2)
        return (
            '<ac:structured-macro ac:name="code">'
            f'<ac:parameter ac:name="language">{lang}</ac:parameter>'
            f'<ac:plain-text-body><![CDATA[{code}]]></ac:plain-text-body>'
            "</ac:structured-macro>"
        )
    md = re.sub(r"```(\w*)\n(.*?)```", _code_block, md, flags=re.DOTALL)

    # Inline code
    md = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", md)

    # Headers (longest prefix first to avoid mis-matching)
    for level in range(6, 0, -1):
        md = re.sub(
            rf"^{'#' * level} (.+)$",
            rf"<h{level}>\1</h{level}>",
            md,
            flags=re.MULTILINE,
        )

    # Bold + italic
    md = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", md)
    md = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", md)
    md = re.sub(r"\*(.+?)\*", r"<em>\1</em>", md)

    # Horizontal rules
    md = re.sub(r"^---+$", "<hr/>", md, flags=re.MULTILINE)

    # Unordered lists
    lines = md.split("\n")
    out: list[str] = []
    in_ul = False
    for line in lines:
        m = re.match(r"^[-*] (.+)$", line)
        if m:
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{m.group(1)}</li>")
        else:
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(line)
    if in_ul:
        out.append("</ul>")
    md = "\n".join(out)

    # Wrap plain text blocks in <p>; leave blocks already starting with a tag
    blocks = re.split(r"\n{2,}", md.strip())
    result: list[str] = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if re.match(r"^<(h[1-6]|ul|ol|hr|ac:|pre|table|p)", block):
            result.append(block)
        else:
            result.append(f"<p>{block.replace(chr(10), '<br/>')}</p>")

    return "\n".join(result)
