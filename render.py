"""
把归一化后的日报数据渲染成 HTML。

输出的 HTML 是自包含的（CSS 内联），既能直接当网页看，
也能被 Playwright 整页截图成一张长图发朋友圈 / 公众号。
"""

import html
import re
from datetime import datetime

import config
from fetch_data import CN_TZ

# 每个版块配一个 emoji，扫读时更好定位
SECTION_ICONS = {
    "模型发布/更新": "🧠",
    "产品发布/更新": "🚀",
    "行业动态": "📊",
    "论文研究": "📄",
    "技巧与观点": "💡",
    "其它": "📌",
}

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def esc(s):
    return html.escape(s or "", quote=True)


def pretty_url(url, limit=52):
    """URL 太长会撑破版面，截断显示。"""
    u = re.sub(r"^https?://", "", url or "")
    return u if len(u) <= limit else u[: limit - 1] + "…"


def format_date_cn(date_str):
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{d.year} 年 {d.month} 月 {d.day} 日 · {WEEKDAYS[d.weekday()]}"
    except Exception:
        return date_str


CSS = """
* { margin:0; padding:0; box-sizing:border-box; }

:root {
  --ink:      #16181d;
  --ink-soft: #3d434e;
  --ink-mute: #767d8a;
  --line:     #e6e8ec;
  --accent:   #1a6b5a;
  --accent-bg:#eef5f2;
  --paper:    #ffffff;
}

body {
  background: #d8dade;
  font-family: "Noto Sans CJK SC", "Source Han Sans SC", "PingFang SC",
               "Microsoft YaHei", -apple-system, sans-serif;
  color: var(--ink);
  -webkit-font-smoothing: antialiased;
}

.page {
  width: 760px;
  margin: 0 auto;
  background: var(--paper);
  padding: 64px 62px 52px;
}

/* ---------- 报头 ---------- */
.masthead { border-bottom: 3px solid var(--ink); padding-bottom: 20px; }

.masthead .kicker {
  display: flex; justify-content: space-between; align-items: baseline;
  font-size: 14px; color: var(--ink-mute); letter-spacing: .08em;
  margin-bottom: 12px;
}
.masthead .brand { font-size: 36px; font-weight: 900; letter-spacing: -.02em; }
.masthead .brand span { color: var(--accent); }
.masthead .dateline {
  margin-top: 10px; font-size: 15px; color: var(--ink-soft); font-weight: 500;
}

/* ---------- 导语 ---------- */
.lead { margin: 30px 0 8px; }
.lead h2 {
  font-size: 23px; font-weight: 800; line-height: 1.5;
  margin-bottom: 14px; letter-spacing: -.01em;
}
.lead p {
  font-size: 16px; line-height: 1.95; color: var(--ink-soft);
  background: var(--accent-bg); border-left: 3px solid var(--accent);
  padding: 16px 20px; border-radius: 0 6px 6px 0;
}

/* ---------- 版块 ---------- */
.section { margin-top: 46px; }
.section-head {
  display: flex; align-items: center; gap: 10px;
  padding-bottom: 10px; margin-bottom: 26px;
  border-bottom: 1px solid var(--line);
}
.section-head .icon { font-size: 20px; }
.section-head .label { font-size: 20px; font-weight: 800; letter-spacing: -.01em; }
.section-head .count {
  margin-left: auto; font-size: 13px; color: var(--ink-mute);
  background: #f2f3f5; padding: 3px 10px; border-radius: 999px;
}

/* ---------- 条目 ---------- */
.item { display: flex; gap: 16px; margin-bottom: 32px; }
.item:last-child { margin-bottom: 0; }

.item .num {
  flex: 0 0 30px; height: 30px; border-radius: 8px;
  background: var(--ink); color: #fff;
  font-size: 14px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
  margin-top: 3px;
}
.item .body { flex: 1; min-width: 0; }

.item h3 {
  font-size: 19px; font-weight: 700; line-height: 1.55;
  letter-spacing: -.01em; margin-bottom: 8px;
}
.item .meta {
  font-size: 13px; color: var(--ink-mute);
  margin-bottom: 10px; font-weight: 500;
}
.item .meta .src { color: var(--accent); font-weight: 700; }
.item .meta .dot { margin: 0 7px; opacity: .5; }

.item p.summary {
  font-size: 15.5px; line-height: 1.95; color: var(--ink-soft);
  margin-bottom: 10px;
}

.item .link {
  font-size: 13px; color: var(--ink-mute);
  padding-left: 12px; border-left: 2px solid var(--line);
  word-break: break-all; line-height: 1.7;
}
.item .link a { color: #2f6fb0; text-decoration: none; }

/* ---------- 点评 ---------- */
.item .comment {
  margin-top: 12px; padding: 13px 16px;
  background: #fbfaf6; border-left: 3px solid #c9a227;
  border-radius: 0 6px 6px 0;
  font-size: 15px; line-height: 1.9; color: var(--ink-soft);
}
.item .comment .tag {
  display: block; font-size: 11.5px; font-weight: 800; letter-spacing: .1em;
  color: #a8871c; margin-bottom: 5px;
}

/* ---------- 结尾一句话 ---------- */
.closing {
  margin-top: 46px; padding: 24px 26px;
  background: var(--ink); color: #f2f3f5; border-radius: 8px;
  font-size: 16px; line-height: 1.95;
}

/* ---------- 推广区块 ---------- */
.promo {
  margin-top: 40px; padding: 28px 26px;
  border: 2px solid var(--ink); border-radius: 8px;
}
.promo h4 { font-size: 20px; font-weight: 800; margin-bottom: 16px; }
.promo .lines { font-size: 15.5px; line-height: 2; color: var(--ink-soft); }
.promo .lines b { color: var(--accent); font-weight: 800; }
.promo .subtitle {
  margin: 18px 0 10px; font-size: 14px; font-weight: 700; color: var(--ink);
}
.promo ul { list-style: none; }
.promo ul li {
  font-size: 15px; line-height: 1.95; color: var(--ink-soft); padding: 3px 0;
}
.promo .cta {
  margin-top: 18px; padding-top: 16px; border-top: 1px dashed var(--line);
  font-size: 14.5px; font-weight: 700; color: var(--accent);
}

/* ---------- 快讯 ---------- */
.flashes { margin-top: 46px; }
.flashes ul { list-style: none; }
.flashes li {
  font-size: 14.5px; line-height: 1.8; color: var(--ink-soft);
  padding: 10px 0 10px 18px; border-bottom: 1px dashed var(--line);
  position: relative;
}
.flashes li:before {
  content: "•"; position: absolute; left: 2px; color: var(--accent); font-weight: 700;
}
.flashes li .m { color: var(--ink-mute); font-size: 12.5px; margin-left: 6px; }

/* ---------- 页脚 ---------- */
.footer {
  margin-top: 54px; padding-top: 22px; border-top: 1px solid var(--line);
  font-size: 12.5px; color: var(--ink-mute); line-height: 1.9; text-align: center;
}
.footer a { color: var(--accent); text-decoration: none; }
.footer .stat { color: var(--ink-soft); font-weight: 600; margin-bottom: 4px; }

.empty { padding: 40px 0; text-align: center; color: var(--ink-mute); font-size: 15px; }
"""


def render_html(data, site_title="AI 日报"):
    d = data
    parts = []
    a = parts.append

    a(f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(site_title)} · {esc(d['date'])}</title>
<style>{CSS}</style>
</head>
<body>
<div class="page">""")

    # ---- 报头 ----
    a(f"""
  <div class="masthead">
    <div class="kicker"><span>AI DAILY BRIEF</span><span>{esc(d['date'])}</span></div>
    <div class="brand">{esc(config.BRAND_MAIN)} <span>{esc(config.BRAND_ACCENT)}</span></div>
    <div class="dateline">{esc(format_date_cn(d['date']))}　|　{esc(d['window'])}</div>
  </div>""")

    # ---- 导语 ----
    if d.get("lead_title") or d.get("lead_paragraph"):
        a('\n  <div class="lead">')
        if d.get("lead_title"):
            a(f'    <h2>{esc(d["lead_title"])}</h2>')
        if d.get("lead_paragraph"):
            a(f'    <p>{esc(d["lead_paragraph"])}</p>')
        a("  </div>")

    # ---- 正文版块（编号全局连续）----
    n = 0
    total = sum(len(s["items"]) for s in d["sections"])

    if total == 0:
        a('\n  <div class="empty">今天暂时没有抓到内容。</div>')

    for sec in d["sections"]:
        icon = SECTION_ICONS.get(sec["label"], "📌")
        a(f"""
  <div class="section">
    <div class="section-head">
      <span class="icon">{icon}</span>
      <span class="label">{esc(sec['label'])}</span>
      <span class="count">{len(sec['items'])} 条</span>
    </div>""")

        for it in sec["items"]:
            n += 1
            meta = []
            if it.get("source"):
                meta.append(f'<span class="src">{esc(it["source"])}</span>')
            if it.get("time_label"):
                meta.append(esc(it["time_label"]))
            meta_html = '<span class="dot">·</span>'.join(meta)

            a(f"""
    <div class="item">
      <div class="num">{n}</div>
      <div class="body">
        <h3>{esc(it['title'])}</h3>""")
            if meta_html:
                a(f'        <div class="meta">{meta_html}</div>')
            if it.get("summary"):
                a(f'        <p class="summary">{esc(it["summary"])}</p>')
            if it.get("url"):
                a(f'        <div class="link">🔗 原文 | '
                  f'<a href="{esc(it["url"])}">{esc(pretty_url(it["url"]))}</a></div>')
            if it.get("comment"):
                a(f'        <div class="comment"><span class="tag">点评</span>'
                  f'{esc(it["comment"])}</div>')
            a("      </div>\n    </div>")

        a("  </div>")

    # ---- 快讯 ----
    if d.get("flashes"):
        a("""
  <div class="flashes">
    <div class="section-head">
      <span class="icon">⚡</span>
      <span class="label">快讯</span>
      <span class="count">%d 条</span>
    </div>
    <ul>""" % len(d["flashes"]))
        for f in d["flashes"]:
            tail = []
            if f.get("source"):
                tail.append(esc(f["source"]))
            if f.get("time_label"):
                tail.append(esc(f["time_label"]))
            a(f'      <li>{esc(f["title"])}'
              f'<span class="m">{" · ".join(tail)}</span></li>')
        a("    </ul>\n  </div>")

    # ---- 结尾一句话 ----
    if d.get("closing"):
        a(f'\n  <div class="closing">{esc(d["closing"])}</div>')

    # ---- 推广区块 ----
    if config.ENABLE_PROMO:
        a('\n  <div class="promo">')
        a(f'    <h4>{esc(config.PROMO_TITLE)}</h4>')
        if config.PROMO_LINES:
            a('    <div class="lines">' +
              "<br>".join(esc(x) for x in config.PROMO_LINES) + "</div>")
        if config.PROMO_BENEFITS:
            if config.PROMO_SUBTITLE:
                a(f'    <div class="subtitle">{esc(config.PROMO_SUBTITLE)}</div>')
            a("    <ul>" +
              "".join(f"<li>{esc(b)}</li>" for b in config.PROMO_BENEFITS) +
              "</ul>")
        if config.PROMO_FOOTER:
            a(f'    <div class="cta">{esc(config.PROMO_FOOTER)}</div>')
        a("  </div>")

    # ---- 页脚 ----
    stamp = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M")
    sig = f"{esc(config.SIGNATURE)}　|　" if config.SIGNATURE else ""
    attribution = (
        f'{sig}数据来源：<a href="https://aihot.virxact.com">AI HOT</a>'
        f'　|　摘要由 AI 生成，引用数字与原话请回原文核对'
        if config.ENABLE_ATTRIBUTION else ""
    )
    a(f"""
  <div class="footer">
    <div class="stat">本期共 {total} 条 · 生成于北京时间 {stamp}</div>
    {attribution}
  </div>
</div>
</body>
</html>""")

    return "\n".join(parts)
