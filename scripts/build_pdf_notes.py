#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build readable PDF full-text notes from /tmp/pdf_full.json."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

RAW_PATH = Path("/tmp/pdf_full.json")
OUT_HTML = Path("/workspace/notes-library.html")
OUT_MD = Path("/workspace/docs/pdf-notes-full.md")

FIELD_RULES = [
    (["建築基準", "都市計画", "農地", "法令上の制限", "盛土", "土地区画"], "法令上の制限"),
    (["抵当", "借地", "賃貸", "時効", "連帯", "保証", "債権", "不法行為", "売主", "権利関係", "担保責任"], "権利関係"),
    (["税", "取得税", "固定資産", "登録免許", "印紙", "譲渡"], "税その他"),
    (["免許", "営業保証", "まとめリスト", "宅建まとめ", "業法"], "宅建業法"),
]

TITLE_REPS = {
    "宅建 権利関係 ① 体系まとめ（知識整理）": "権利関係 体系まとめ",
    "宅建まとめリスト（完全版 第2版）": "まとめリスト（完全版）",
    "法令上の制限まとめリスト（主要ポイント整理）": "法令上の制限まとめリスト（簡易）",
    "第1章 農地法の基本": "農地法まとめ",
    "第1章 借地権の基本": "借地権まとめ",
    "第1章 不動産取得税（頻出）": "税金まとめ（取得税・固定資産税・登録免許税など）",
    "抵当権まとめ（宅建 権利関係）": "抵当権まとめ",
    "賃貸借まとめ（宅建重要ポイント）": "賃貸借まとめ",
    "売主の担保責任まとめ（宅建）": "売主の担保責任まとめ",
    "連帯債務と保証債務まとめ（宅建 権利関係）": "連帯債務と保証債務まとめ",
    "時効まとめ（宅建 権利関係）": "時効まとめ",
}

SECTION_START = re.compile(
    r"^(第\d+章|【|[✅📘📗📚📌■⚠🏠🧾⏳]|[①②③④⑤⑥⑦⑧⑨⑩]|要点|まとめポイント|試験)"
)
BULLET = re.compile(r"^[・●▪]|^\-\s")


def field_of(title: str) -> str:
    for keys, field in FIELD_RULES:
        if any(k in title for k in keys):
            return field
    return "その他"


def clean_title(title: str) -> str:
    title = re.sub(r"^[📘📗📚📌🏠🧾⏳✅■⚠\s【]+", "", title or "")
    title = title.replace("】", "").strip()
    title = re.sub(r"\s+", " ", title)
    return TITLE_REPS.get(title, title)


def slugify(title: str) -> str:
    s = re.sub(r"[^\w一-龥ぁ-んァ-ンー]+", "-", title, flags=re.UNICODE)
    return s.strip("-")[:90] or "note"


def is_section(s: str) -> bool:
    s = (s or "").strip()
    if not s:
        return False
    if SECTION_START.match(s):
        return True
    return bool(re.match(r"^\d+[\.．]\s*\S", s) and len(s) < 48)


HEADER_DENY = {
    "住居系", "商業系", "工業系",
}

def is_headerish(s: str) -> bool:
    """Likely table header label (short noun-like)."""
    s = (s or "").strip()
    if not s or len(s) > 14:
        return False
    if s in HEADER_DENY:
        return False
    if is_section(s) or BULLET.match(s) or s.startswith("|"):
        return False
    if re.search(r"[。！？]", s):
        return False
    # sentence-like values
    if re.search(r"[がをにでは]", s) and len(s) > 8:
        return False
    if re.fullmatch(r"[\d,，\.％%㎡ha円万]+", s):
        return False
    return True


def soft_join(lines: list[str]) -> list[str]:
    out: list[str] = []
    buf = ""
    for raw in lines:
        line = (raw or "").strip()
        if not line:
            if buf:
                out.append(buf)
                buf = ""
            out.append("")
            continue
        if not buf:
            buf = line
            continue

        if line.startswith(("（", "(")) and not re.search(r"[。！？!?]$", buf):
            buf += line
            continue

        if re.search(r"【[^】]*$", buf) or (
            buf.endswith(("①", "②", "③", "④")) and not is_section(line) and not is_headerish(line)
        ):
            buf += line
            continue

        if is_section(buf) or is_section(line) or BULLET.match(buf) or BULLET.match(line):
            out.append(buf)
            buf = line
            continue

        ends = bool(re.search(r"[。！？!?：:）」』]$", buf))
        wrap = (not ends) and len(buf) >= 24 and not is_headerish(line) and not is_headerish(buf)
        wrap = wrap or (
            (not ends)
            and not is_headerish(buf)
            and line.startswith(("・", "および", "または", "／", "/", "③", "④"))
        )
        if wrap:
            buf += line
        else:
            out.append(buf)
            buf = line
    if buf:
        out.append(buf)
    return out


def parse_pipe_table(line: str):
    if "|" not in line or line.count("|") < 3:
        return None
    chunks = [c.strip() for c in line.split("|")]
    chunks = [c for c in chunks if c and not re.fullmatch(r":?-{3,}:?", c)]
    if len(chunks) < 4:
        return None
    for ncols in (4, 3):
        if len(chunks) < ncols * 2:
            continue
        headers = chunks[:ncols]
        body = chunks[ncols:]
        rows = [body[i : i + ncols] for i in range(0, len(body) - ncols + 1, ncols)]
        rows = [r for r in rows if len(r) == ncols]
        if rows:
            return headers, rows
    return None


def try_table(lines: list[str], i: int):
    pipe = parse_pipe_table(lines[i])
    if pipe:
        return pipe[0], pipe[1], i + 1

    # Only start a table if the first line looks like a header label.
    if not is_headerish(lines[i]):
        return None

    best = None
    for ncols in range(5, 1, -1):
        if i + ncols - 1 >= len(lines):
            continue
        hh = [lines[i + c].strip() for c in range(ncols)]
        if not all(is_headerish(h) for h in hh):
            continue

        k = i + ncols
        rows: list[list[str]] = []
        while k + ncols - 1 < len(lines):
            cells = []
            ok = True
            for c in range(ncols):
                s = lines[k + c].strip()
                if not s or is_section(s) or BULLET.match(s) or s.startswith("|"):
                    ok = False
                    break
                cells.append(s)
            if not ok:
                break
            if ncols == 2 and len(cells[0]) > 48 and "。" in cells[0]:
                break
            rows.append(cells)
            k += ncols
            if len(rows) > 60:
                break

        if len(rows) < (2 if ncols <= 2 else 1):
            continue
        if ncols >= 4 and len(rows) < 2:
            continue

        score = len(rows) * ncols + ncols * 25
        score += sum(3 for r in rows if len(r[0]) <= 24)
        score += sum(5 for r in rows if len(r[0]) <= 24 and any(len(c) > 26 for c in r[1:]))
        score -= sum(12 for r in rows if len(r[0]) > 30)
        if rows and all(is_headerish(c) or len(c) <= 14 for c in rows[0]):
            score -= 90
        # Misparsed wider table often yields many short/short header-like pairs
        if ncols == 2:
            both_headerish = sum(1 for r in rows if is_headerish(r[0]) and is_headerish(r[1]))
            if both_headerish >= max(2, int(len(rows) * 0.5)):
                score -= 100
        # Classic 2-col: two labels then key + long value
        if (
            ncols == 2
            and i + 3 < len(lines)
            and is_headerish(lines[i])
            and is_headerish(lines[i + 1])
            and is_headerish(lines[i + 2])
            and not is_headerish(lines[i + 3])
            and len(lines[i + 3].strip()) > 20
        ):
            score += 80
        score += sum(2 for h in hh if len(h) <= 8)

        if best is None or score > best[0]:
            best = (score, hh, rows, k)

    if not best or best[0] < 8:
        return None
    _, hh, rows, k = best
    return hh, rows, k


def strip_decor(s: str) -> str:
    s = s.replace("**", "")
    s = re.sub(r"^[✅\s]+", "", s)
    return s.strip()


def to_blocks(lines: list[str]):
    joined = soft_join(lines)
    blocks = []
    i = 0
    n = len(joined)
    while i < n:
        s = joined[i].strip()
        if not s:
            i += 1
            continue

        parsed = try_table(joined, i)
        if parsed:
            hh, rows, ni = parsed
            if ni > i + 1 and rows:
                blocks.append(
                    (
                        "table",
                        {
                            "headers": [strip_decor(h) for h in hh],
                            "rows": [[strip_decor(c) for c in r] for r in rows],
                        },
                    )
                )
                i = ni
                continue

        if re.match(r"^第\d+章", s) or (s.startswith("【") and "】" in s):
            label = s.strip("【")
            if "】" in label:
                label = label.split("】", 1)[0]
            blocks.append(("h2", strip_decor(label)))
            i += 1
            continue
        if s.startswith(("✅", "📘", "📗", "📚", "📌", "■", "🏠", "🧾", "⏳")) or re.match(r"^[①-⑩]", s):
            label = strip_decor(re.sub(r"^[✅📘📗📚📌■🏠🧾⏳\s]+", "", s))
            blocks.append(("h3", label))
            i += 1
            continue
        if s.startswith(("⚠", "※")):
            blocks.append(("callout", strip_decor(s)))
            i += 1
            continue
        if BULLET.match(s) or s.startswith("・"):
            items = []
            while i < n:
                t = joined[i].strip()
                if not t or not (BULLET.match(t) or t.startswith("・")):
                    break
                items.append(strip_decor(re.sub(r"^[・●▪\-]\s*", "", t)))
                i += 1
            blocks.append(("ul", items))
            continue

        blocks.append(("p", strip_decor(s)))
        i += 1
    return blocks


def render_table_html(headers: list[str], rows: list[list[str]]) -> str:
    if len(headers) <= 2:
        thead = "<thead><tr>" + "".join(f"<th>{html.escape(h)}</th>" for h in headers) + "</tr></thead>"
        body = []
        for r in rows:
            cells = []
            for idx, c in enumerate(r):
                if idx == 0:
                    cells.append(f'<th scope="row">{html.escape(c)}</th>')
                else:
                    cells.append(f"<td>{html.escape(c)}</td>")
            body.append("<tr>" + "".join(cells) + "</tr>")
        return f'<div class="table-wrap"><table>{thead}<tbody>{"".join(body)}</tbody></table></div>'

    cards = []
    for r in rows:
        title = html.escape(r[0])
        kv = []
        for h, c in zip(headers[1:], r[1:]):
            kv.append(
                f'<div class="kv"><span class="k">{html.escape(h)}</span>'
                f'<span class="v">{html.escape(c)}</span></div>'
            )
        cards.append(f'<div class="kv-card"><div class="kv-title">{title}</div>{"".join(kv)}</div>')
    return '<div class="kv-list">' + "".join(cards) + "</div>"


def blocks_to_html(blocks) -> str:
    parts = []
    for kind, data in blocks:
        if kind == "h2":
            parts.append(f"<h2>{html.escape(data)}</h2>")
        elif kind == "h3":
            parts.append(f"<h3>{html.escape(data)}</h3>")
        elif kind == "callout":
            parts.append(f'<div class="callout">{html.escape(data)}</div>')
        elif kind == "p":
            parts.append(f"<p>{html.escape(data)}</p>")
        elif kind == "ul":
            parts.append("<ul>" + "".join(f"<li>{html.escape(x)}</li>" for x in data) + "</ul>")
        elif kind == "table":
            parts.append(render_table_html(data["headers"], data["rows"]))
    return "\n".join(parts)


def blocks_to_md(blocks, title: str, field: str) -> str:
    out = [f"## {title}", "", f"> 分野: {field}", ""]
    for kind, data in blocks:
        if kind == "h2":
            out += [f"### {data}", ""]
        elif kind == "h3":
            out += [f"#### {data}", ""]
        elif kind == "callout":
            out += [f"> {data}", ""]
        elif kind == "p":
            out += [data, ""]
        elif kind == "ul":
            out += [f"- {x}" for x in data] + [""]
        elif kind == "table":
            hh, rows = data["headers"], data["rows"]
            if len(hh) <= 2:
                out.append("| " + " | ".join(hh) + " |")
                out.append("| " + " | ".join(["---"] * len(hh)) + " |")
                for r in rows:
                    out.append("| " + " | ".join(r) + " |")
                out.append("")
            else:
                for r in rows:
                    out.append(f"**{r[0]}**")
                    for h, c in zip(hh[1:], r[1:]):
                        out.append(f"- {h}: {c}")
                    out.append("")
    return "\n".join(out)


def select_notes(raw: list[dict]) -> list[dict]:
    selected = []
    for i, item in enumerate(raw):
        if i == 18:
            continue
        title = clean_title(item["title"])
        selected.append(
            {
                "title": title,
                "field": field_of(title),
                "lines": item.get("lines") or [],
                "text": item.get("text") or "",
                "chars": len(item.get("text") or ""),
            }
        )
    by_title = {}
    for n in selected:
        if n["title"] not in by_title or n["chars"] > by_title[n["title"]]["chars"]:
            by_title[n["title"]] = n
    notes = list(by_title.values())
    order = {"法令上の制限": 0, "権利関係": 1, "税その他": 2, "宅建業法": 3, "その他": 9}
    notes.sort(key=lambda n: (order.get(n["field"], 9), n["title"]))
    seen: dict[str, int] = {}
    for n in notes:
        base = slugify(n["title"])
        if base in seen:
            seen[base] += 1
            n["id"] = f"{base}-{seen[base]}"
        else:
            seen[base] = 0
            n["id"] = base
    return notes


def build() -> None:
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    notes = select_notes(raw)

    for n in notes:
        lines = list(n["lines"])
        if lines and (
            clean_title(lines[0]) == n["title"] or n["title"] in lines[0] or lines[0] in n["title"]
        ):
            lines = lines[1:]
        blocks = to_blocks(lines)
        n["html"] = blocks_to_html(blocks)
        n["md"] = blocks_to_md(blocks, n["title"], n["field"])
        if len(n["html"]) < 80:
            n["html"] = "\n".join(
                f"<p>{html.escape(p.strip())}</p>" for p in n["text"].split("\n") if p.strip()
            )

    md = [
        "# PDF全文ノート（宅建）",
        "",
        "アップロードPDFの全文を分野別に読みやすく整理したノートです。",
        "",
        "同じ内容の閲覧ページ: [`notes-library.html`](../notes-library.html)",
        "",
        "## 目次",
        "",
    ]
    for n in notes:
        md.append(f"- [{n['title']}](#{n['id']})（{n['field']}・{n['chars']}字）")
    md.append("")
    for n in notes:
        md.append(f'<a id="{n["id"]}"></a>\n')
        md.append(n["md"])
        md.append("\n---\n")
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    notes_json = json.dumps(
        [{"id": n["id"], "title": n["title"], "field": n["field"], "chars": n["chars"]} for n in notes],
        ensure_ascii=False,
    )
    articles = []
    for n in notes:
        articles.append(
            f'<article class="note" id="{html.escape(n["id"])}" data-field="{html.escape(n["field"])}">\n'
            f'  <header class="note-head">\n'
            f'    <div class="field-pill">{html.escape(n["field"])}</div>\n'
            f'    <h1>{html.escape(n["title"])}</h1>\n'
            f'    <div class="meta">{n["chars"]}字 · PDF全文</div>\n'
            f"  </header>\n"
            f'  <div class="note-body">\n{n["html"]}\n  </div>\n'
            f"</article>"
        )

    page = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>
<meta name="theme-color" content="#1a2332"/>
<title>PDF全文ノート｜宅建</title>
<style>
:root {{
  --bg:#171e2a; --bg2:#1f2a3a; --card:#243246; --text:#f2f5f8; --muted:#9aadc4;
  --accent:#e8a54b; --accent2:#5eb8a8; --line:rgba(255,255,255,.08);
}}
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;background:var(--bg);color:var(--text);
  font-family:"Hiragino Sans","Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif;
  line-height:1.75; -webkit-text-size-adjust:100%}}
body{{min-height:100dvh;padding-bottom:96px}}
.top{{
  position:sticky;top:0;z-index:30;
  background:linear-gradient(180deg,#121926 0%,rgba(23,30,42,.97) 100%);
  border-bottom:1px solid var(--line);backdrop-filter:blur(8px);
  padding:12px 16px 10px;
}}
.top h1{{margin:0;font-size:1.1rem}}
.top .sub{{color:var(--muted);font-size:.75rem;margin-top:4px}}
.top-links{{margin-top:6px;font-size:.75rem}}
.top-links a{{color:var(--accent2);text-decoration:none;margin-right:12px}}
.search{{
  width:100%;margin-top:10px;padding:11px 12px;border-radius:12px;
  border:1px solid var(--line);background:var(--bg2);color:var(--text);font-size:.92rem;
}}
.mode-row,.filters,.note-tabs{{display:flex;gap:6px;overflow-x:auto;scrollbar-width:none}}
.mode-row{{padding:8px 16px 0}}
.filters{{padding:10px 16px 4px}}
.note-tabs{{padding:6px 16px 10px}}
.mode-row::-webkit-scrollbar,.filters::-webkit-scrollbar,.note-tabs::-webkit-scrollbar{{display:none}}
.mode-btn,.ftab,.ntab{{
  flex:0 0 auto;border:1px solid var(--line);background:var(--bg2);color:var(--muted);
  border-radius:999px;padding:8px 12px;font-size:.74rem;cursor:pointer;
}}
.mode-btn.active,.ftab.active,.ntab.active{{
  background:var(--accent);color:#1a2332;border-color:transparent;font-weight:800;
}}
.toc{{
  background:var(--bg2);border:1px solid var(--line);border-radius:14px;
  padding:14px;margin:4px 16px 0;
}}
.toc h2{{margin:0 0 8px;font-size:.9rem}}
.toc a{{display:block;color:var(--accent2);text-decoration:none;font-size:.82rem;
  padding:6px 0;border-bottom:1px solid var(--line)}}
.toc a:last-child{{border-bottom:0}}
.toc .f{{color:var(--muted);font-size:.68rem;margin-right:6px}}
main{{max-width:760px;margin:0 auto;padding:8px 16px 24px}}
.note{{display:none;background:var(--card);border:1px solid var(--line);border-radius:18px;padding:18px 16px;margin-bottom:14px}}
.note.show{{display:block}}
.note-head{{margin-bottom:14px;padding-bottom:12px;border-bottom:1px solid var(--line)}}
.field-pill{{
  display:inline-block;font-size:.68rem;padding:3px 8px;border-radius:999px;
  background:rgba(94,184,168,.14);color:var(--accent2);margin-bottom:8px;
}}
.note-head h1{{margin:0;font-size:1.2rem;line-height:1.45}}
.meta{{color:var(--muted);font-size:.72rem;margin-top:6px}}
.note-body h2{{font-size:1.02rem;margin:1.25em 0 .45em;color:var(--accent)}}
.note-body h3{{font-size:.95rem;margin:1em 0 .35em;color:#d7e6f5}}
.note-body p{{margin:.55em 0;font-size:.92rem;color:#e8eef5}}
.note-body ul{{margin:.45em 0 .8em;padding-left:1.15em}}
.note-body li{{margin:.28em 0;font-size:.9rem}}
.callout{{
  margin:.8em 0;padding:10px 12px;border-radius:10px;
  background:rgba(232,165,75,.12);border:1px solid rgba(232,165,75,.28);
  color:#f0d2a0;font-size:.88rem;
}}
.table-wrap{{overflow-x:auto;margin:.9em 0;border-radius:12px;border:1px solid var(--line)}}
table{{width:100%;border-collapse:collapse;font-size:.82rem;min-width:280px}}
th,td{{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}
thead th{{background:rgba(0,0,0,.22);color:var(--accent2);font-weight:700;white-space:nowrap}}
tbody th{{background:rgba(94,184,168,.08);color:#cfe9e3;font-weight:700;min-width:6.5em}}
tr:last-child td,tr:last-child th{{border-bottom:0}}
.kv-list{{display:grid;gap:10px;margin:.9em 0}}
.kv-card{{
  border:1px solid var(--line);border-radius:12px;padding:12px;
  background:rgba(0,0,0,.14);
}}
.kv-title{{font-weight:800;color:var(--accent2);margin-bottom:8px;font-size:.92rem}}
.kv{{display:grid;grid-template-columns:7.5em 1fr;gap:8px;padding:6px 0;border-top:1px solid var(--line);font-size:.82rem}}
.kv:first-of-type{{border-top:0}}
.kv .k{{color:var(--muted)}}
.kv .v{{color:#e8eef5}}
.empty{{color:var(--muted);text-align:center;padding:40px 16px}}
.hidden{{display:none !important}}
footer.bar{{
  position:fixed;left:0;right:0;bottom:0;
  background:rgba(18,25,38,.96);border-top:1px solid var(--line);
  padding:10px 16px calc(10px + env(safe-area-inset-bottom));
  display:flex;gap:8px;justify-content:center;
}}
footer.bar a{{
  flex:1;max-width:220px;text-align:center;text-decoration:none;
  border-radius:12px;padding:12px;font-weight:800;font-size:.88rem;
}}
.btn-primary{{background:var(--accent);color:#1a2332}}
.btn-ghost{{background:var(--bg2);color:var(--text);border:1px solid var(--line)}}
</style>
</head>
<body>
<header class="top">
  <h1>PDF全文ノート</h1>
  <div class="sub">添付PDF {len(notes)}本を分野別に読みやすく整理 · 全文収録</div>
  <div class="top-links">
    <a href="./weakness-daily.html">弱点振り返り</a>
    <a href="./docs/pdf-notes-full.md">Markdown版</a>
    <a href="./start.html">スタート</a>
  </div>
  <input class="search" id="q" type="search" placeholder="キーワード検索（例: 建蔽率 / 法定地上権 / 3000万）" enterkeyhint="search"/>
</header>
<div class="mode-row">
  <button class="mode-btn active" type="button" data-mode="one">1本ずつ読む</button>
  <button class="mode-btn" type="button" data-mode="all">ヒットを一覧</button>
</div>
<nav class="filters" id="fields"></nav>
<nav class="note-tabs" id="noteTabs"></nav>
<section class="toc" id="toc"></section>
<main id="main">
{''.join(articles)}
  <div class="empty hidden" id="empty">該当するノートがありません</div>
</main>
<footer class="bar">
  <a class="btn-ghost" href="./weakness-daily.html">弱点振り返り</a>
  <a class="btn-primary" href="./start.html">スタートへ</a>
</footer>
<script>
const NOTES = {notes_json};
const fields = ['すべて', ...Array.from(new Set(NOTES.map(n => n.field)))];
let field = 'すべて';
let activeId = NOTES[0]?.id || null;
let mode = 'one';
function esc(s){{
  return String(s).replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));
}}
function filtered() {{
  const q = document.getElementById('q').value.trim().toLowerCase();
  return NOTES.filter(n => {{
    if (field !== 'すべて' && n.field !== field) return false;
    if (!q) return true;
    const art = document.getElementById(n.id);
    const hay = (n.title + ' ' + n.field + ' ' + (art ? art.innerText : '')).toLowerCase();
    return hay.includes(q);
  }});
}}
function renderChrome() {{
  const list = filtered();
  document.getElementById('fields').innerHTML = fields.map(f =>
    `<button class="ftab${{f===field?' active':''}}" type="button" data-field="${{esc(f)}}">${{esc(f)}}</button>`
  ).join('');
  document.getElementById('fields').querySelectorAll('.ftab').forEach(b => b.onclick = () => {{
    field = b.dataset.field; activeId = null; render();
  }});
  document.getElementById('noteTabs').innerHTML = list.map(n => {{
    const short = n.title.replace('まとめノート','').replace('まとめ','').slice(0, 14);
    return `<button class="ntab${{n.id===activeId?' active':''}}" type="button" data-id="${{n.id}}">${{esc(short)}}</button>`;
  }}).join('');
  document.getElementById('noteTabs').querySelectorAll('.ntab').forEach(b => b.onclick = () => {{
    activeId = b.dataset.id; mode = 'one';
    document.querySelectorAll('.mode-btn').forEach(x => x.classList.toggle('active', x.dataset.mode==='one'));
    show();
    document.getElementById(activeId)?.scrollIntoView({{behavior:'smooth', block:'start'}});
  }});
  document.getElementById('toc').innerHTML = `<h2>目次（${{list.length}}本）</h2>` + list.map(n =>
    `<a href="#${{n.id}}" data-id="${{n.id}}"><span class="f">${{esc(n.field)}}</span>${{esc(n.title)}}</a>`
  ).join('');
  document.getElementById('toc').querySelectorAll('a').forEach(a => a.onclick = (e) => {{
    e.preventDefault();
    activeId = a.dataset.id; mode = 'one';
    document.querySelectorAll('.mode-btn').forEach(x => x.classList.toggle('active', x.dataset.mode==='one'));
    show();
    document.getElementById(activeId)?.scrollIntoView({{behavior:'smooth', block:'start'}});
  }});
}}
function show() {{
  const list = filtered();
  if (!list.length) {{
    document.querySelectorAll('.note').forEach(n => n.classList.remove('show'));
    document.getElementById('empty').classList.remove('hidden');
    renderChrome();
    return;
  }}
  document.getElementById('empty').classList.add('hidden');
  if (!activeId || !list.some(n => n.id === activeId)) activeId = list[0].id;
  const q = document.getElementById('q').value.trim();
  const showAll = mode === 'all' || !!q;
  document.querySelectorAll('.note').forEach(n => {{
    const on = list.some(x => x.id === n.id) && (showAll || n.id === activeId);
    n.classList.toggle('show', on);
  }});
  renderChrome();
}}
function render() {{ renderChrome(); show(); }}
document.getElementById('q').addEventListener('input', () => {{ activeId = null; render(); }});
document.querySelectorAll('.mode-btn').forEach(b => b.onclick = () => {{
  mode = b.dataset.mode;
  document.querySelectorAll('.mode-btn').forEach(x => x.classList.toggle('active', x === b));
  render();
}});
render();
</script>
</body>
</html>
"""
    OUT_HTML.write_text(page, encoding="utf-8")

    print(f"notes={len(notes)}")
    for key in [
        "建築基準法まとめノート（前編）",
        "都市計画法まとめノート（前編）",
        "都市計画法まとめノート（中編）",
        "売主の担保責任まとめ",
    ]:
        n = next((x for x in notes if x["title"] == key), None)
        if not n:
            print("missing", key)
            continue
        has = ("table-wrap" in n["html"]) or ("kv-list" in n["html"])
        print(f"  {key}: structured={has} html_len={len(n['html'])}")
        m = re.search(r'<div class="(?:table-wrap|kv-list)">.*?</div>', n["html"], re.S)
        if m:
            print("   ", re.sub(r"\s+", " ", m.group(0))[:240])
    print(f"wrote {OUT_HTML} ({OUT_HTML.stat().st_size})")
    print(f"wrote {OUT_MD} ({OUT_MD.stat().st_size})")


if __name__ == "__main__":
    build()
